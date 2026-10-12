package tfhe

import (
	"github.com/sp301415/tfhe-go/math/num"
	"github.com/sp301415/tfhe-go/math/poly"
	"github.com/sp301415/tfhe-go/math/vec"
)

// LookUpTable is a polynomial that is the lookup table
// for function evaluations during programmable bootstrapping.
type LookUpTable[T TorusInt] struct {
	// Value has length polyExtendFactor.
	Value     []poly.Poly[T]
	CountLUTs int
}

// NewLookUpTable creates a new lookup table.
func NewLookUpTable[T TorusInt](params Parameters[T]) LookUpTable[T] {
	lut := make([]poly.Poly[T], params.polyExtendFactor)
	for i := 0; i < params.polyExtendFactor; i++ {
		lut[i] = poly.NewPoly[T](params.polyDegree)
	}

	return LookUpTable[T]{Value: lut}
}

// NewLookUpTableCustom creates a new lookup table with custom size.
func NewLookUpTableCustom[T TorusInt](extendFactor, polyDegree int) LookUpTable[T] {
	lut := make([]poly.Poly[T], extendFactor)
	for i := 0; i < extendFactor; i++ {
		lut[i] = poly.NewPoly[T](polyDegree)
	}

	return LookUpTable[T]{Value: lut}
}

// Copy returns a copy of the LUT.
func (lut LookUpTable[T]) Copy() LookUpTable[T] {
	lutCopy := make([]poly.Poly[T], len(lut.Value))
	for i := 0; i < len(lut.Value); i++ {
		lutCopy[i] = lut.Value[i].Copy()
	}
	return LookUpTable[T]{Value: lutCopy}
}

// CopyFrom copies values from the LUT.
func (lut *LookUpTable[T]) CopyFrom(lutIn LookUpTable[T]) {
	for i := 0; i < len(lut.Value); i++ {
		lut.Value[i].CopyFrom(lutIn.Value[i])
	}
}

// Clear clears the LUT.
func (lut *LookUpTable[T]) Clear() {
	for i := 0; i < len(lut.Value); i++ {
		lut.Value[i].Clear()
	}
}

// GenLookUpTable generates a lookup table based on function f.
// Input and output of f is cut by MessageModulus.
func (e *Evaluator[T]) GenLookUpTable(f func(int) int) LookUpTable[T] {
	lutOut := NewLookUpTable(e.Parameters)
	e.GenLookUpTableAssign(f, lutOut)
	return lutOut
}

// GenLookUpTableAssign generates a lookup table based on function f and writes it to lutOut.
// Input and output of f is cut by MessageModulus.
func (e *Evaluator[T]) GenLookUpTableAssign(f func(int) int, lutOut LookUpTable[T]) {
	e.GenLookUpTableCustomAssign(f, e.Parameters.messageModulus, e.Parameters.scale, lutOut)
}

// GenManyLookUpTablesAssign generates a lookup table based on functions funcs and writes it to lutOut.
// Input and output of each function in funcs is cut by MessageModulus.
func (e *Evaluator[T]) GenManyLookUpTablesAssign(funcs [](func(int) int), lutOut LookUpTable[T]) {
	e.GenManyLookUpTablesCustomAssign(funcs, e.Parameters.messageModulus, e.Parameters.scale, lutOut)
}

// GenLookUpTableFull generates a lookup table based on function f.
// Output of f is encoded as-is.
func (e *Evaluator[T]) GenLookUpTableFull(f func(int) T) LookUpTable[T] {
	lutOut := NewLookUpTable(e.Parameters)
	e.GenLookUpTableFullAssign(f, lutOut)
	return lutOut
}

// GenLookUpTableFullAssign generates a lookup table based on function f and writes it to lutOut.
// Output of f is encoded as-is.
func (e *Evaluator[T]) GenLookUpTableFullAssign(f func(int) T, lutOut LookUpTable[T]) {
	e.GenLookUpTableCustomFullAssign(f, e.Parameters.messageModulus, lutOut)
}

// GenLookUpTableCustom generates a lookup table based on function f using custom messageModulus and scale.
// Input and output of f is cut by messageModulus.
func (e *Evaluator[T]) GenLookUpTableCustom(f func(int) int, messageModulus, scale T) LookUpTable[T] {
	lutOut := NewLookUpTable(e.Parameters)
	e.GenLookUpTableCustomAssign(f, messageModulus, scale, lutOut)
	return lutOut
}

// GenLookUpTableCustomAssign generates a lookup table based on function f using custom messageModulus and scale and writes it to lutOut.
// Input and output of f is cut by messageModulus.
func (e *Evaluator[T]) GenLookUpTableCustomAssign(f func(int) int, messageModulus, scale T, lutOut LookUpTable[T]) {
	e.GenLookUpTableCustomFullAssign(func(x int) T { return e.EncodeLWECustom(f(x), messageModulus, scale).Value }, messageModulus, lutOut)
}

// GenManyLookUpTablesCustomAssign generates a lookup table based on functions funcs using custom messageModulus and scale and writes it to lutOut.
// Input and output of each function in funcs is cut by messageModulus.
func (e *Evaluator[T]) GenManyLookUpTablesCustomAssign(funcs [](func(int) int), messageModulus, scale T, lutOut LookUpTable[T]) {
	e.GenManyLookUpTablesCustomFullAssign(func(x int) []T {
		valList := make([]T, len(funcs))
		for i := range funcs {
			valList[i] = e.EncodeLWECustom(funcs[i](x), messageModulus, scale).Value
		}
		return valList
	}, messageModulus, lutOut)
}

// GenLookUpTableCustomFull generates a lookup table based on function f using custom messageModulus and scale.
// Output of f is encoded as-is.
func (e *Evaluator[T]) GenLookUpTableCustomFull(f func(int) T, messageModulus T) LookUpTable[T] {
	lutOut := NewLookUpTable(e.Parameters)
	e.GenLookUpTableCustomFullAssign(f, messageModulus, lutOut)
	return lutOut
}

// GenLookUpTableCustomFullAssign generates a lookup table based on function f using custom messageModulus and scale and writes it to lutOut.
// Output of f is encoded as-is.
//
// In the full-torus case, the LUT works only for the positive half of the plaintext space, while the negative half is extended through negacyclicity
func (e *Evaluator[T]) GenLookUpTableCustomFullAssign(f func(int) T, messageModulus T, lutOut LookUpTable[T]) {
	if e.Parameters.FullTorus() {
		messageModulus /= 2
	}
	for x := 0; x < int(messageModulus); x++ {
		start := num.DivRound(x*e.Parameters.lookUpTableSize, int(messageModulus))
		end := num.DivRound((x+1)*e.Parameters.lookUpTableSize, int(messageModulus))
		y := f(x)
		for xx := start; xx < end; xx++ {
			e.buffer.lutRaw[xx] = y
		}
	}

	offset := num.DivRound(e.Parameters.lookUpTableSize, int(2*messageModulus))
	if messageModulus == T(e.Parameters.lookUpTableSize) {
		// no redundancy at all
		offset = 0
	}
	vec.RotateInPlaceNegacyclic(e.buffer.lutRaw, -offset)

	for i := 0; i < e.Parameters.polyExtendFactor; i++ {
		for j := 0; j < e.Parameters.polyDegree; j++ {
			lutOut.Value[i].Coeffs[j] = e.buffer.lutRaw[j*e.Parameters.polyExtendFactor+i]
		}
	}
}

// GenLookUpTableCustomFullAssign generates a lookup table based on function f using custom messageModulus and scale and writes it to lutOut.
// Output of f is encoded as-is.
//
// In the full-torus case, the LUT works only for the positive half of the plaintext space, while the negative half is extended through negacyclicity
func (e *Evaluator[T]) GenManyLookUpTablesCustomFullAssign(f func(int) []T, messageModulus T, lutOut LookUpTable[T]) {
	if e.Parameters.FullTorus() {
		messageModulus /= 2
	}
	if e.Parameters.fullDomain {
		messageModulus *= 2
	}
	countLUTs := e.Parameters.countLUTs
	mvGap := e.Parameters.mvGap[0]
	for x := 0; x < int(messageModulus); x++ {
		start := num.DivRound(x*e.Parameters.lookUpTableSize, int(messageModulus))
		end := start + mvGap
		y := f(x)
		for xx := start; xx < end; xx++ {
			for i := range y {
				e.buffer.lutRaw[xx+i*mvGap] = y[i]
			}
		}
	}

	offset := mvGap / 2
	if messageModulus*T(countLUTs) == T(e.Parameters.lookUpTableSize) {
		// no redundancy at all
		offset = 0
	}
	vec.RotateInPlaceNegacyclic(e.buffer.lutRaw, -offset)

	for i := 0; i < e.Parameters.polyExtendFactor; i++ {
		for j := 0; j < e.Parameters.polyDegree; j++ {
			lutOut.Value[i].Coeffs[j] = e.buffer.lutRaw[j*e.Parameters.polyExtendFactor+i]
		}
	}
}
