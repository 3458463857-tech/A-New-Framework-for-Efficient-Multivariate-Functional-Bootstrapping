package main

import (
	. "github.com/mmcloughlin/avo/build"
	. "github.com/mmcloughlin/avo/operand"
)

func decomposeConstants() {
	ConstData("ONE", U64(1))
	ConstData("Const64", U64(64))
}

func decomposePolyAssignUint32AVX2() {
	TEXT("decomposePolyAssignUint32AVX2", NOSPLIT, "func(p []uint32, base uint32, logBase uint32, logLastBaseQ uint32, decomposedOut [][]uint32)")
	Pragma("noescape")

	p := Load(Param("p").Base(), GP64())
	decomposedOut := Load(Param("decomposedOut").Base(), GP64())

	N := Load(Param("p").Len(), GP64())
	level := Load(Param("decomposedOut").Len(), GP64())

	// VET: go vet complains about VBROADCASTD on uint32 values.
	// See https://github.com/golang/go/issues/47625.
	base, logBase, logLastBaseQ := YMM(), YMM(), YMM()
	VPBROADCASTD(NewParamAddr("base", 24), base)
	VPBROADCASTD(NewParamAddr("logBase", 28), logBase)
	VPBROADCASTD(NewParamAddr("logLastBaseQ", 32), logLastBaseQ)

	one := YMM()
	VPBROADCASTD(NewDataAddr(NewStaticSymbol("ONE"), 0), one)

	baseMask, baseHalf, logBaseSubOne := YMM(), YMM(), YMM()
	VPSUBD(one, base, baseMask)
	VPSRLD(Imm(1), base, baseHalf)
	VPSUBD(one, logBase, logBaseSubOne)

	i := GP64()
	XORQ(i, i)
	JMP(LabelRef("N_loop_end"))
	Label("N_loop_body")

	c := YMM()
	VMOVDQU(Mem{Base: p, Index: i, Scale: 4}, c)

	cDiv, cCarry := YMM(), YMM()
	VPSRLVD(logLastBaseQ, c, cDiv)
	VPSLLD(Imm(1), c, cCarry)
	VPSRLVD(logLastBaseQ, cCarry, cCarry)
	VANDPD(one, cCarry, cCarry)
	VPADDD(cCarry, cDiv, c)

	j := GP64()
	MOVQ(level, j)
	SUBQ(Imm(1), j)

	jj := GP64()
	MOVQ(j, jj)
	ADDQ(j, jj)
	ADDQ(j, jj)
	JMP(LabelRef("level_loop_end"))
	Label("level_loop_body")

	u := YMM()
	VANDPD(baseMask, c, u)
	VPSRLVD(logBase, c, c)

	uDiv := YMM()
	VPSRLVD(logBaseSubOne, u, uDiv)
	VPADDD(uDiv, c, c)

	uCarry := YMM()
	VANDPD(baseHalf, u, uCarry)
	VPSLLD(Imm(1), uCarry, uCarry)
	VPSUBD(uCarry, u, u)

	decomposedOutj := GP64()
	MOVQ(Mem{Base: decomposedOut, Index: jj, Scale: 8}, decomposedOutj)
	VMOVDQU(u, Mem{Base: decomposedOutj, Index: i, Scale: 4})

	SUBQ(Imm(1), j)
	SUBQ(Imm(3), jj)

	Label("level_loop_end")
	CMPQ(j, Imm(1))
	JGE(LabelRef("level_loop_body"))

	u = YMM()
	VANDPD(baseMask, c, u)

	uCarry = YMM()
	VANDPD(baseHalf, u, uCarry)
	VPSLLD(Imm(1), uCarry, uCarry)
	VPSUBD(uCarry, u, u)

	decomposedOut0 := GP64()
	MOVQ(Mem{Base: decomposedOut}, decomposedOut0)
	VMOVDQU(u, Mem{Base: decomposedOut0, Index: i, Scale: 4})

	ADDQ(Imm(8), i)

	Label("N_loop_end")
	CMPQ(i, N)
	JL(LabelRef("N_loop_body"))

	RET()
}

func decomposePolyAssignUint64AVX2() {
	TEXT("decomposePolyAssignUint64AVX2", NOSPLIT, "func(p []uint64, base uint64, logBase uint64, logLastBaseQ uint64, decomposedOut [][]uint64)")
	Pragma("noescape")

	p := Load(Param("p").Base(), GP64())
	decomposedOut := Load(Param("decomposedOut").Base(), GP64())

	N := Load(Param("p").Len(), GP64())
	level := Load(Param("decomposedOut").Len(), GP64())

	base, logBase, logLastBaseQ := YMM(), YMM(), YMM()
	VPBROADCASTQ(NewParamAddr("base", 24), base)
	VPBROADCASTQ(NewParamAddr("logBase", 32), logBase)
	VPBROADCASTQ(NewParamAddr("logLastBaseQ", 40), logLastBaseQ)

	one := YMM()
	VPBROADCASTQ(NewDataAddr(NewStaticSymbol("ONE"), 0), one)

	baseMask, baseHalf, logBaseSubOne := YMM(), YMM(), YMM()
	VPSUBQ(one, base, baseMask)    // baseMask = base - 1
	VPSRLQ(Imm(1), base, baseHalf) // baseHalf = base/2
	VPSUBQ(one, logBase, logBaseSubOne)

	i := GP64()
	XORQ(i, i)
	JMP(LabelRef("N_loop_end"))
	Label("N_loop_body")

	c := YMM()
	VMOVDQU(Mem{Base: p, Index: i, Scale: 8}, c)

	cDiv, cCarry := YMM(), YMM()
	VPSRLVQ(logLastBaseQ, c, cDiv) // cDiv = c >> logLastBaseQ
	VPSLLQ(Imm(1), c, cCarry)
	VPSRLVQ(logLastBaseQ, cCarry, cCarry)
	VANDPD(one, cCarry, cCarry) // cCarry = ((c << 1) >> logLastBaseQ) & 1 = MSB of remainder
	VPADDQ(cCarry, cDiv, c)     // cDiv = (c >> logLastBaseQ) + cCarry = DivRound(c, 2^logLastBaseQ)

	j := GP64()
	MOVQ(level, j)
	SUBQ(Imm(1), j) // j = level - 1

	jj := GP64()
	MOVQ(j, jj)
	ADDQ(j, jj)
	ADDQ(j, jj) // jj = 3*j  // each entry in decomposedOut is a slice -> 3*8 bytes
	JMP(LabelRef("level_loop_end"))
	Label("level_loop_body")

	u := YMM()
	VANDPD(baseMask, c, u) // u = remainder
	VPSRLVQ(logBase, c, c) // c = quotient

	uDiv := YMM()
	VPSRLVQ(logBaseSubOne, u, uDiv) // uDiv = MSB of remainder
	VPADDQ(uDiv, c, c)              // c += uDiv

	uCarry := YMM()
	VANDPD(baseHalf, u, uCarry)
	VPSLLQ(Imm(1), uCarry, uCarry) // uCarry = uDiv * base
	VPSUBQ(uCarry, u, u)           // u -= uCarry

	decomposedOutj := GP64()
	MOVQ(Mem{Base: decomposedOut, Index: jj, Scale: 8}, decomposedOutj)
	VMOVDQU(u, Mem{Base: decomposedOutj, Index: i, Scale: 8})

	SUBQ(Imm(1), j)  // j -= 1
	SUBQ(Imm(3), jj) // jj = 3*j

	Label("level_loop_end")
	CMPQ(j, Imm(1)) // while j >= 1
	JGE(LabelRef("level_loop_body"))

	u = YMM()
	VANDPD(baseMask, c, u)

	uCarry = YMM()
	VANDPD(baseHalf, u, uCarry)
	VPSLLQ(Imm(1), uCarry, uCarry)
	VPSUBQ(uCarry, u, u) // center u into [-B/2, B/2)

	decomposedOut0 := GP64()
	MOVQ(Mem{Base: decomposedOut}, decomposedOut0)
	VMOVDQU(u, Mem{Base: decomposedOut0, Index: i, Scale: 8})

	ADDQ(Imm(4), i)

	Label("N_loop_end")
	CMPQ(i, N) // while i < N
	JL(LabelRef("N_loop_body"))

	RET()
}

// func decomposePolyAssignUint64AVX2New() {
// 	TEXT("decomposePolyAssignUint64AVX2New", NOSPLIT, "func(p []uint64, base uint64, logBase uint64, logLastBaseQ uint64, decomposedOut [][]uint64)")
// 	Pragma("noescape")

// 	p := Load(Param("p").Base(), GP64())
// 	decomposedOut := Load(Param("decomposedOut").Base(), GP64())

// 	N := Load(Param("p").Len(), GP64())
// 	level := Load(Param("decomposedOut").Len(), GP64())

// 	one, const64 := YMM(), YMM()
// 	VPBROADCASTQ(NewDataAddr(NewStaticSymbol("ONE"), 0), one)
// 	VPBROADCASTQ(NewDataAddr(NewStaticSymbol("Const64"), 0), const64)

// 	logBase, logBasePlusOne := YMM(), YMM()
// 	VPBROADCASTQ(NewParamAddr("logBase", 32), logBase)
// 	VPADDQ(one, logBase, logBasePlusOne)

// 	i := GP64()
// 	XORQ(i, i)
// 	JMP(LabelRef("N_loop_end"))
// 	Label("N_loop_body")

// 	c := YMM()
// 	VMOVDQU(Mem{Base: p, Index: i, Scale: 8}, c)

// 	// shift right by 1 bit to make the highest digit centered
// 	VPSRAQ(Imm(1), c, c)

// 	j := GP64()
// 	XORQ(j, j) // j = 0

// 	shiftBitsLeft, shiftBitsRight := YMM(), YMM()
// 	VMOVDQU(logBasePlusOne, shiftBitsLeft)
// 	VPSUBQ(logBasePlusOne, const64, shiftBitsRight)

// 	jj := GP64()
// 	XORQ(jj, jj) // jj = 3*j  // each entry in decomposedOut is a slice -> 3*8 bytes
// 	JMP(LabelRef("level_loop_end"))
// 	Label("level_loop_body")

// 	// c is always the remainder in the inner loop, while u is the quotient
// 	u := YMM()
// 	VMOVDQU(c, u)
// 	VPSLLVQ(shiftBitsLeft, c, c)
// 	VPSRAVQ(shiftBitsLeft, c, c) // c = (c << shiftBitsLeft) >> shiftBitsLeft

// 	VPSUBQ(c, u, u)
// 	VPSRAVQ(shiftBitsRight, u, u) // u = (u - c) >> shiftBitsRight

// 	decomposedOutj := GP64()
// 	MOVQ(Mem{Base: decomposedOut, Index: jj, Scale: 8}, decomposedOutj)
// 	VMOVDQU(u, Mem{Base: decomposedOutj, Index: i, Scale: 8})

// 	ADDQ(Imm(1), j)                                 // j += 1
// 	ADDQ(Imm(3), jj)                                // jj = 3*j
// 	VPADDQ(logBase, shiftBitsLeft, shiftBitsLeft)   // shiftBitsLeft = (j+1)*logBase
// 	VPSUBQ(logBase, shiftBitsRight, shiftBitsRight) // shiftBitsRight = 64 - shiftBitsLeft

// 	Label("level_loop_end")
// 	CMPQ(j, level) // while j < level
// 	JL(LabelRef("level_loop_body"))

// 	ADDQ(Imm(4), i) // i += 4

// 	Label("N_loop_end")
// 	CMPQ(i, N) // while i < N
// 	JL(LabelRef("N_loop_body"))

// 	RET()
// }
