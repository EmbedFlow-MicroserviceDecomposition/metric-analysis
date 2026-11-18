// Command ms070analyzer type-checks boulder (non-test code) and reports:
//   - every call whose callee method takes a trailing ...grpc.CallOption (a gRPC client call),
//     with the enclosing function, receiver type, the callee interface/type and method;
//   - every gRPC service registration (&X_ServiceDesc, impl) with the impl's concrete type;
//   - every method declared on each concrete type (to resolve promoted/embedded methods).
package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/token"
	"go/types"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/tools/go/packages"
)

type callSite struct {
	File       string `json:"file"`
	Line       int    `json:"line"`
	CallerPkg  string `json:"caller_pkg"`
	CallerRecv string `json:"caller_recv"` // receiver type of the enclosing method ("" for plain funcs)
	CallerName string `json:"caller_pkgname"` // Go package name (partition classes use name.Type)
	CallerFunc string `json:"caller_func"`
	CalleeType string `json:"callee_type"` // pkgpath.TypeName of the interface/type declaring the method
	Method     string `json:"method"`
	Text       string `json:"text"`
}

type registration struct {
	File     string   `json:"file"`
	Line     int      `json:"line"`
	Desc     string   `json:"desc"`      // e.g. sapb.StorageAuthority_ServiceDesc
	DescPkg  string   `json:"desc_pkg"`  // import path of the proto package
	ImplType string   `json:"impl_type"` // pkgpath.TypeName of the concrete implementation
	Methods  []string `json:"methods"`   // full method set of *Impl (including promoted)
	Owners   []string `json:"owners"`    // for each method: pkgpath.TypeName that declares it
}

func named(t types.Type) *types.Named {
	for {
		switch tt := t.(type) {
		case *types.Pointer:
			t = tt.Elem()
		case *types.Named:
			return tt
		default:
			return nil
		}
	}
}

func typeName(n *types.Named) string {
	if n == nil || n.Obj() == nil || n.Obj().Pkg() == nil {
		return ""
	}
	return n.Obj().Pkg().Path() + "." + n.Obj().Name()
}

func isCallOptionVariadic(sig *types.Signature) bool {
	if sig == nil || !sig.Variadic() || sig.Params().Len() == 0 {
		return false
	}
	last := sig.Params().At(sig.Params().Len() - 1).Type()
	sl, ok := last.(*types.Slice)
	if !ok {
		return false
	}
	n := named(sl.Elem())
	return n != nil && n.Obj().Name() == "CallOption" && strings.HasSuffix(n.Obj().Pkg().Path(), "google.golang.org/grpc")
}

func main() {
	root, _ := filepath.Abs(os.Args[1])
	cfg := &packages.Config{
		Mode:  packages.NeedName | packages.NeedFiles | packages.NeedSyntax | packages.NeedTypes | packages.NeedTypesInfo,
		Dir:   root,
		Tests: false,
		Env:   append(os.Environ(), "GOFLAGS=-mod=vendor", "CGO_ENABLED=1"),
	}
	pkgs, err := packages.Load(cfg, "./...")
	if err != nil {
		panic(err)
	}
	var calls []callSite
	var libcalls []callSite
	var methodValues []callSite
	var funcValueCalls []callSite
	var regs []registration
	nerr := 0
	lines := map[string][]string{}
	lineText := func(fset *token.FileSet, p token.Pos) (string, int, string) {
		pos := fset.Position(p)
		rel, _ := filepath.Rel(root, pos.Filename)
		if _, ok := lines[pos.Filename]; !ok {
			b, _ := os.ReadFile(pos.Filename)
			lines[pos.Filename] = strings.Split(string(b), "\n")
		}
		return rel, pos.Line, strings.TrimSpace(lines[pos.Filename][pos.Line-1])
	}
	for _, p := range pkgs {
		nerr += len(p.Errors)
		for i, e := range p.Errors {
			if nerr-len(p.Errors)+i < 8 {
				fmt.Fprintln(os.Stderr, p.PkgPath, "::", e)
			}
		}
		if strings.Contains(p.PkgPath, "/vendor/") || !strings.HasPrefix(p.PkgPath, "github.com/letsencrypt/boulder") {
			continue
		}
		for _, f := range p.Syntax {
			fname := p.Fset.Position(f.Pos()).Filename
			if strings.HasSuffix(fname, ".pb.go") {
				continue // generated client stubs call conn.Invoke themselves
			}
			for _, d := range f.Decls {
				fd, ok := d.(*ast.FuncDecl)
				if !ok || fd.Body == nil {
					continue
				}
				recv := ""
				if fd.Recv != nil && len(fd.Recv.List) > 0 {
					if n := named(p.TypesInfo.TypeOf(fd.Recv.List[0].Type)); n != nil {
						recv = typeName(n)
					}
				}
				called := map[*ast.SelectorExpr]bool{}
				ast.Inspect(fd.Body, func(n ast.Node) bool {
					if ce, ok := n.(*ast.CallExpr); ok {
						if sel, ok := ce.Fun.(*ast.SelectorExpr); ok {
							called[sel] = true
						}
					}
					return true
				})
				ast.Inspect(fd.Body, func(n ast.Node) bool {
					if sel, ok := n.(*ast.SelectorExpr); ok && !called[sel] {
						if s := p.TypesInfo.Selections[sel]; s != nil && s.Kind() == types.MethodVal {
							if sig, ok := s.Obj().Type().(*types.Signature); ok && isCallOptionVariadic(sig) {
								callee := typeName(named(s.Recv()))
								rel, ln, txt := lineText(p.Fset, sel.Pos())
								methodValues = append(methodValues, callSite{rel, ln, p.PkgPath, recv, p.Name, fd.Name.Name, callee, sel.Sel.Name, txt})
							}
						}
					}
					ce, ok := n.(*ast.CallExpr)
					if !ok {
						return true
					}
					if _, isSel := ce.Fun.(*ast.SelectorExpr); !isSel {
						if sig, ok := p.TypesInfo.TypeOf(ce.Fun).(*types.Signature); ok && isCallOptionVariadic(sig) {
							rel, ln, txt := lineText(p.Fset, ce.Pos())
							funcValueCalls = append(funcValueCalls, callSite{rel, ln, p.PkgPath, recv, p.Name, fd.Name.Name, "func-value", fmt.Sprint(ce.Fun), txt})
						}
					}
					// gRPC server registration: something(&X_ServiceDesc, impl)
					if len(ce.Args) >= 2 {
						if ue, ok := ce.Args[0].(*ast.UnaryExpr); ok {
							if sel, ok := ue.X.(*ast.SelectorExpr); ok && strings.HasSuffix(sel.Sel.Name, "_ServiceDesc") {
								impl := named(p.TypesInfo.TypeOf(ce.Args[1]))
								rel, ln, _ := lineText(p.Fset, ce.Pos())
								r := registration{File: rel, Line: ln, Desc: fmt.Sprint(sel.X) + "." + sel.Sel.Name, ImplType: typeName(impl)}
								if obj := p.TypesInfo.Uses[sel.Sel]; obj != nil && obj.Pkg() != nil {
									r.DescPkg = obj.Pkg().Path()
								}
								if impl != nil {
									ms := types.NewMethodSet(types.NewPointer(impl))
									for i := 0; i < ms.Len(); i++ {
										m := ms.At(i).Obj()
										r.Methods = append(r.Methods, m.Name())
										owner := ""
										if sig, ok := m.Type().(*types.Signature); ok && sig.Recv() != nil {
											owner = typeName(named(sig.Recv().Type()))
										}
										r.Owners = append(r.Owners, owner)
									}
								}
								regs = append(regs, r)
							}
						}
					}
					sel, ok := ce.Fun.(*ast.SelectorExpr)
					if !ok {
						return true
					}
					if f, ok := p.TypesInfo.Uses[sel.Sel].(*types.Func); ok && f.Pkg() != nil && f.Name() == "VerifyCSR" && strings.HasSuffix(f.Pkg().Path(), "/csr") && p.Name != "csr" {
						rel, ln, txt := lineText(p.Fset, ce.Pos())
						libcalls = append(libcalls, callSite{rel, ln, p.PkgPath, recv, p.Name, fd.Name.Name, "csr", "VerifyCSR", txt})
					}
					s := p.TypesInfo.Selections[sel]
					if s == nil || s.Kind() != types.MethodVal {
						return true
					}
					fn, ok := s.Obj().(*types.Func)
					if !ok {
						return true
					}
					sig, _ := fn.Type().(*types.Signature)
					if fn.Pkg() != nil && p.Name != fn.Pkg().Name() && (strings.HasSuffix(fn.Pkg().Path(), "/ctpolicy") ||
						(strings.HasSuffix(fn.Pkg().Path(), "/goodkey") && fn.Name() == "GoodKey") ||
						(strings.HasSuffix(fn.Pkg().Path(), "/csr") && fn.Name() == "VerifyCSR")) {
						rel, ln, txt := lineText(p.Fset, ce.Pos())
						libcalls = append(libcalls, callSite{rel, ln, p.PkgPath, recv, p.Name, fd.Name.Name, "ctpolicy", sel.Sel.Name, txt})
					}
					if !isCallOptionVariadic(sig) {
						return true
					}
					callee := ""
					if sig.Recv() != nil {
						callee = typeName(named(sig.Recv().Type()))
					}
					if callee == "" { // interface method: use the static type of the receiver expression
						callee = typeName(named(s.Recv()))
					}
					rel, ln, txt := lineText(p.Fset, ce.Pos())
					calls = append(calls, callSite{rel, ln, p.PkgPath, recv, p.Name, fd.Name.Name, callee, sel.Sel.Name, txt})
					return true
				})
			}
		}
	}
	out := map[string]any{"load_errors": nerr, "calls": calls, "library_callers": libcalls, "method_values": methodValues, "func_value_calls": funcValueCalls, "registrations": regs}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", " ")
	_ = enc.Encode(out)
}
