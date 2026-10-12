package tfhe

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"math"
	"math/bits"

	"github.com/sp301415/tfhe-go/math/num"
	"github.com/sp301415/tfhe-go/math/vec"
)

// TorusInt represents the integers living in the discretized torus.
// Currently, it supports Q = 2^32 and Q = 2^64 (uint32 and uint64).
type TorusInt interface {
	uint32 | uint64
}

// GadgetParametersLiteral is a structure for Gadget Decomposition,
// which is used in Lev, GSW, GLev and GGSW encryptions.
type GadgetParametersLiteral[T TorusInt] struct {
	// Base is a base of gadget. It must be power of two.
	Base T
	// Level is a length of gadget.
	Level int
}

// WithBase sets the base and returns the new GadgetParametersLiteral.
func (p GadgetParametersLiteral[T]) WithBase(base T) GadgetParametersLiteral[T] {
	p.Base = base
	return p
}

// WithLevel sets the level and returns the new GadgetParametersLiteral.
func (p GadgetParametersLiteral[T]) WithLevel(level int) GadgetParametersLiteral[T] {
	p.Level = level
	return p
}

// Compile transforms GadgetParametersLiteral to read-only GadgetParameters.
// If there is any invalid parameter in the literal, it panics.
func (p GadgetParametersLiteral[T]) Compile() GadgetParameters[T] {
	switch {
	case p.Base < 2:
		panic("Base smaller than two")
	case !num.IsPowerOfTwo(p.Base):
		panic("Base not power of two")
	case p.Level <= 0:
		panic("Level smaller than zero")
	case num.SizeT[T]() < num.Log2(p.Base)*p.Level:
		panic("Base * Level larger than Q")
	}

	return GadgetParameters[T]{
		base:    p.Base,
		logBase: num.Log2(p.Base),
		level:   p.Level,
		sizeT:   num.SizeT[T](),
	}
}

// GadgetParameters is a read-only, compiled parameters based on GadgetParametersLiteral.
type GadgetParameters[T TorusInt] struct {
	// Base is a base of gadget. It must be power of two.
	base T
	// LogBase equals log(Base).
	logBase int
	// Level is a length of gadget.
	level int
	// sizeT is the size of T in bits.
	sizeT int
}

// Base is a base of gadget. It must be power of two.
func (p GadgetParameters[T]) Base() T {
	return p.base
}

// LogBase equals log(Base).
func (p GadgetParameters[T]) LogBase() int {
	return p.logBase
}

// Level is a length of gadget.
func (p GadgetParameters[T]) Level() int {
	return p.level
}

// BaseQ returns Q / Base^(i+1) for 0 <= i < Level.
// For the most common usages i = 0 and i = Level-1, use [GadgetParameters.FirstBaseQ] and [GadgetParameters.LastBaseQ].
func (p GadgetParameters[T]) BaseQ(i int) T {
	return T(1 << (p.sizeT - (i+1)*p.logBase))
}

// FirstBaseQ returns Q / Base.
func (p GadgetParameters[T]) FirstBaseQ() T {
	return T(1 << (p.sizeT - p.logBase))
}

// LastBaseQ returns Q / Base^Level.
func (p GadgetParameters[T]) LastBaseQ() T {
	return T(1 << (p.sizeT - p.level*p.logBase))
}

// LogBaseQ returns log(Q / Base^(i+1)) for 0 <= i < Level.
// For the most common usages i = 0 and i = Level-1, use [GadgetParameters.LogFirstBaseQ] and [GadgetParameters.LogLastBaseQ].
func (p GadgetParameters[T]) LogBaseQ(i int) int {
	return p.sizeT - (i+1)*p.logBase
}

// LogFirstBaseQ returns log(Q / Base).
func (p GadgetParameters[T]) LogFirstBaseQ() int {
	return p.sizeT - p.logBase
}

// LogLastBaseQ returns log(Q / Base^Level).
func (p GadgetParameters[T]) LogLastBaseQ() int {
	return p.sizeT - p.level*p.logBase
}

// Literal returns a GadgetParametersLiteral from this GadgetParameters.
func (p GadgetParameters[T]) Literal() GadgetParametersLiteral[T] {
	return GadgetParametersLiteral[T]{
		Base:  p.base,
		Level: p.level,
	}
}

// ByteSize returns the byte size of the gadget parameters.
func (p GadgetParameters[T]) ByteSize() int {
	return 16
}

// WriteTo implements the [io.WriterTo] interface.
//
// The encoded form is as follows:
//
//	[8] Base
//	[8] Level
func (p GadgetParameters[T]) WriteTo(w io.Writer) (n int64, err error) {
	var nWrite int
	var buf [8]byte

	base := p.base
	binary.BigEndian.PutUint64(buf[:], uint64(base))

	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	level := p.level
	binary.BigEndian.PutUint64(buf[:], uint64(level))
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	if n < int64(p.ByteSize()) {
		return n, io.ErrShortWrite
	}

	return
}

// ReadFrom implements the [io.ReaderFrom] interface.
func (p *GadgetParameters[T]) ReadFrom(r io.Reader) (n int64, err error) {
	var nRead int
	var buf [8]byte

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	base := T(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	level := int(binary.BigEndian.Uint64(buf[:]))

	*p = GadgetParametersLiteral[T]{
		Base:  base,
		Level: level,
	}.Compile()

	return
}

// MarshalBinary implements the [encoding.BinaryMarshaler] interface.
func (p GadgetParameters[T]) MarshalBinary() (data []byte, err error) {
	buf := bytes.NewBuffer(make([]byte, 0, p.ByteSize()))
	_, err = p.WriteTo(buf)
	return buf.Bytes(), err
}

// UnmarshalBinary implements the [encoding.BinaryUnmarshaler] interface.
func (p *GadgetParameters[T]) UnmarshalBinary(data []byte) error {
	buf := bytes.NewBuffer(data)
	_, err := p.ReadFrom(buf)
	return err
}

// BootstrapOrder is an enum type for the order of Programmable Bootstrapping.
type BootstrapOrder int

const (
	// OrderKeySwitchBlindRotate sets the order of Programmable Bootstrapping as
	//
	//	KeySwitch -> BlindRotate -> SampleExtract
	//
	// This means that LWE keys and ciphertexts will have size
	// according to GLWEDimension.
	// Public key encryption is supported only with this order.
	OrderKeySwitchBlindRotate BootstrapOrder = iota

	// OrderBlindRotateKeySwitch sets the order of Programmable Bootstrapping as
	//
	//	BlindRotate -> SampleExtract -> KeySwitch
	//
	// This means that LWE keys and ciphertexts will have size
	// according to LWEDimension.
	// Public key encryption is not supported with this order.
	OrderBlindRotateKeySwitch
)

var gaussianKList32to256 []float64 = []float64{
	6.33796, 6.44394, 6.54828, 6.65104, 6.75231, 6.85213, 6.95058, 7.04770,
	7.14356, 7.23818, 7.33163, 7.42394, 7.51516, 7.60531, 7.69445, 7.78260,
	7.86978, 7.95604, 8.04140, 8.12590, 8.20954, 8.29236, 8.37439, 8.45565,
	8.53615, 8.61591, 8.69497, 8.77333, 8.85101, 8.92803, 9.00441, 9.08016,
	9.15530, 9.22984, 9.30379, 9.37718, 9.45001, 9.52229, 9.59405, 9.66527,
	9.73599, 9.80621, 9.87594, 9.94518, 10.01396, 10.08228, 10.15015, 10.21758,
	10.28456, 10.35113, 10.41728, 10.48301, 10.54835, 10.61329, 10.67785, 10.74201,
	10.80581, 10.86924, 10.93230, 10.99501, 11.05737, 11.11938, 11.18106, 11.24240,
	11.30341, 11.36411, 11.42448, 11.48455, 11.54430, 11.60375, 11.66290, 11.72176,
	11.78033, 11.83861, 11.89661, 11.95433, 12.01178, 12.06896, 12.12587, 12.18252,
	12.23892, 12.29506, 12.35094, 12.40658, 12.46197, 12.51712, 12.57203, 12.62670,
	12.68115, 12.73535, 12.78934, 12.84310, 12.89664, 12.94996, 13.00306, 13.05595,
	13.10863, 13.16110, 13.21337, 13.26543, 13.31729, 13.36895, 13.42042, 13.47169,
	13.52276, 13.57365, 13.62434, 13.67486, 13.72519, 13.77534, 13.82530, 13.87510,
	13.92471, 13.97415, 14.02341, 14.07250, 14.12143, 14.17019, 14.21878, 14.26721,
	14.31548, 14.36359, 14.41153, 14.45932, 14.50696, 14.55443, 14.60176, 14.64894,
	14.69596, 14.74284, 14.78957, 14.83615, 14.88259, 14.92889, 14.97504, 15.02106,
	15.06693, 15.11266, 15.15826, 15.20372, 15.24906, 15.29425, 15.33931, 15.38425,
	15.42905, 15.47373, 15.51827, 15.56269, 15.60699, 15.65115, 15.69520, 15.73913,
	15.78293, 15.82662, 15.87018, 15.91362, 15.95695, 16.00016, 16.04326, 16.08624,
	16.12911, 16.17186, 16.21451, 16.25704, 16.29946, 16.34177, 16.38398, 16.42608,
	16.46807, 16.50995, 16.55173, 16.59340, 16.63498, 16.67645, 16.71781, 16.75907,
	16.80024, 16.84130, 16.88227, 16.92313, 16.96390, 17.00457, 17.04515, 17.08563,
	17.12601, 17.16630, 17.20650, 17.24659, 17.28661, 17.32653, 17.36636, 17.40609,
	17.44574, 17.48530, 17.52476, 17.56414, 17.60344, 17.64265, 17.68177, 17.72080,
	17.75975, 17.79861, 17.83739, 17.87609, 17.91470, 17.95323, 17.99168, 18.03005,
	18.06834, 18.10654, 18.14467, 18.18272, 18.22068, 18.25857, 18.29638, 18.33412,
	18.37177, 18.40935, 18.44686, 18.48429, 18.52164, 18.55891, 18.59612, 18.63325,
	18.67030,
}

// GaussianBoundForFailureProb returns the Gaussian bound for a given failure probability
func GaussianBoundForFailureProb(logFaliureProb int) float64 {
	switch {
	case logFaliureProb >= -256 && logFaliureProb <= -32:
		return gaussianKList32to256[-logFaliureProb-32]
	case logFaliureProb == 0:
		return gaussianKList32to256[64-32] // 2^-64
	default:
		panic("expecting logFailureProb in [-256, -32] or 0 (default for 64 bits)")
	}
}

// ParametersLiteral is a structure for TFHE parameters.
//
// # Warning
//
// Unless you are a cryptographic expert, DO NOT set these by yourself;
// always use the default parameters provided.
type ParametersLiteral[T TorusInt] struct {
	// LWEDimension is the dimension of LWE lattice used. Usually this is denoted by n.
	LWEDimension int
	// GLWERank is the rank of GLWE lattice used. Usually this is denoted by k.
	// Length of GLWE secret key is GLWERank, and length of GLWE ciphertext is GLWERank+1.
	GLWERank int
	// PolyDegree is the degree of polynomials in GLWE entities. Usually this is denoted by N.
	PolyDegree int
	// LookUpTableSize is the size of the Lookup Table used in Blind Rotation.
	//
	// In case of Extended Bootstrapping, this may differ from PolyDegree as explained in https://eprint.iacr.org/2023/402.
	// Therefore, it must be a multiple of PolyDegree.
	// To use the original TFHE bootstrapping, set this to PolyDegree.
	//
	// If zero, then it is set to PolyDegree.
	LookUpTableSize int

	// LWEStdDev is the normalized standard deviation used for gaussian error sampling in LWE encryption.
	LWEStdDev float64
	// GLWEStdDev is the normalized standard deviation used for gaussian error sampling in GLWE encryption.
	GLWEStdDev float64

	// BlockSize is the size of block to be used for LWE key sampling.
	//
	// This is used in Block Binary Key distribution, as explained in https://eprint.iacr.org/2023/958.
	// To use the original TFHE bootstrapping, set this to 1.
	//
	// If zero, then it is set to 1.
	BlockSize int

	// MessageModulus is the modulus of the encoded message.
	MessageModulus T

	// BlindRotateParameters is the gadget parameters for Blind Rotation.
	BlindRotateParameters GadgetParametersLiteral[T]
	// KeySwitchParameters is the gadget parameters for KeySwitching.
	KeySwitchParameters GadgetParametersLiteral[T]

	// BootstrapOrder is the order of Programmable Bootstrapping.
	// If this is set to OrderKeySwitchBlindRotate, then the order is:
	//
	//	KeySwitch -> BlindRotate -> SampleExtract
	//
	// and LWE keys and ciphertexts will have size according to GLWEDimension.
	//
	// Otherwise, if this is set to OrderBlindRotateKeySwitch, the order is:
	//
	//	BlindRotate -> SampleExtract -> KeySwitch
	//
	// and LWE keys and ciphertexts will have size according to LWEDimension.
	//
	// Essentially, there is a time-memory tradeoff:
	// performing keyswitching first means that it will consume more memory,
	// but it allows to use smaller parameters which will result in faster computation.
	//
	// Moreover, public key encryption is supported only with OrderKeySwitchBlindRotate.
	//
	// If zero, then it is set to OrderKeySwitchBlindRotate.
	BootstrapOrder BootstrapOrder

	// WorstCaseLogFailureProb is the Log2(failure probability) when estimating the upper bound
	// of a Gaussian distribution
	//
	// A zero value means 2^-64 failure probability
	//
	// Nonzero values consist of integers between -32 and -256
	//
	// Meta-FBS applies this probability to each perturbation bound. Callers must
	// manually reserve a union-bound margin for the desired overall failure probability.
	WorstCaseLogFailureProb int

	// FullTorus == true means the plaintexts modulo p are encoded as Q/p*m
	//
	// Otherwise, the plaintexts are encoded as Q/(2p)*m for arbitrary LUT evaluation
	//
	// Defaults to false
	FullTorus bool

	// MetaFBS == true to use meta functional bootstrap
	MetaFBS bool

	// ItersCount is the number of iterations in Meta-FBS
	ItersCount int

	// RepeatBase is the factor by which the exponent is upscaled during the truncated repetitions
	//
	// Equivalently, this is the ratio between the ring dimensions for ring switching
	RepeatBase []int

	// TruncationBound is the number of coefficients to keep during the truncated repetitions
	TruncationBound []int

	// ExtendedCoeffsCount is the number of extended (garbage) coefficients during the truncated repetitions
	ExtendedCoeffsCount []int

	// TruncatedRepetitionParameters is the gadget parameters for the truncated repetitions
	TruncatedRepetitionParameters []GadgetParametersLiteral[T]

	// CountLUTs is the number of LUTs evaluated in a single Meta-FBS
	//
	// set to 0 or 1 for a regular single-value bootstrap
	//
	// set to >1 for a PBSManyLUT [CLOT21]
	//
	// NOTE: PBSManyLUTs for non-meta FBS is not implemented
	CountLUTs int

	// FullDomain == true to use full domain functional bootstrap
	FullDomain bool

	// CountCancelSignLUTs is the number of LUTs in the multi-value FDFB-CancelSign at the end of Meta-FDFB
	CountCancelSignLUTs int

	// ExtraRedundancyInExtraction is the number of redundant coefficients during sample extraction, default to 1
	//
	// The higher this value, the faster/smaller LWE-to-RLWE packing in Meta-FDFB, but Meta-FBS may become slower or even unavailable
	TargetRedundancyInExtraction int

	// // LazyCancelSign == true means a scalar is gadget-multiplied with the subLUT entries in blind rotation result
	// // before CancelSign
	// LazyCancelSign bool

	// If the input noise can be regarded as a centered Gaussian, we can obtain lower noise bounds durint TruncRepeat
	InputNoiseIsGaussian bool

	// Sets to true to test the performance of PFKS (with dummy PFKS keys)
	IsDummyPublicFunctionalKeySwitch bool
}

// WithLWEDimension sets the LWEDimension and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithLWEDimension(lweDimension int) ParametersLiteral[T] {
	p.LWEDimension = lweDimension
	return p
}

// WithGLWERank sets the GLWERank and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithGLWERank(glweRank int) ParametersLiteral[T] {
	p.GLWERank = glweRank
	return p
}

// WithPolyDegree sets the PolyDegree and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithPolyDegree(polyDegree int) ParametersLiteral[T] {
	p.PolyDegree = polyDegree
	return p
}

// WithLookUpTableSize sets the LookUpTableSize and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithLookUpTableSize(lookUpTableSize int) ParametersLiteral[T] {
	p.LookUpTableSize = lookUpTableSize
	return p
}

// WithLWEStdDev sets the LWEStdDev and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithLWEStdDev(lweStdDev float64) ParametersLiteral[T] {
	p.LWEStdDev = lweStdDev
	return p
}

// WithGLWEStdDev sets the GLWEStdDev and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithGLWEStdDev(glweStdDev float64) ParametersLiteral[T] {
	p.GLWEStdDev = glweStdDev
	return p
}

// WithBlockSize sets the BlockSize and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithBlockSize(blockSize int) ParametersLiteral[T] {
	p.BlockSize = blockSize
	return p
}

// WithMessageModulus sets the MessageModulus and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithMessageModulus(messageModulus T) ParametersLiteral[T] {
	p.MessageModulus = messageModulus
	return p
}

// WithBlindRotateParameters sets the BlindRotateParameters and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithBlindRotateParameters(blindRotateParameters GadgetParametersLiteral[T]) ParametersLiteral[T] {
	p.BlindRotateParameters = blindRotateParameters
	return p
}

// WithKeySwitchParameters sets the KeySwitchParameters and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithKeySwitchParameters(keySwitchParameters GadgetParametersLiteral[T]) ParametersLiteral[T] {
	p.KeySwitchParameters = keySwitchParameters
	return p
}

// WithBootstrapOrder sets the BootstrapOrder and returns the new ParametersLiteral.
func (p ParametersLiteral[T]) WithBootstrapOrder(bootstrapOrder BootstrapOrder) ParametersLiteral[T] {
	p.BootstrapOrder = bootstrapOrder
	return p
}

// WithWorstCaseLogFailureProb sets the WorstCaseLogFailureProb and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithWorstCaseLogFailureProb(worstCaseLogFailureProb int) ParametersLiteral[T] {
	p.WorstCaseLogFailureProb = worstCaseLogFailureProb
	return p
}

// WithFullTorus sets the FullTorus and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithFullTorus(fullTorus bool) ParametersLiteral[T] {
	p.FullTorus = fullTorus
	return p
}

// WithMetaFBS sets the MetaFBS and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithMetaFBS(metaFBS bool) ParametersLiteral[T] {
	p.MetaFBS = metaFBS
	return p
}

// WithItersCount sets the ItersCount and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithItersCount(itersCount int) ParametersLiteral[T] {
	p.ItersCount = itersCount
	return p
}

// WithRepeatBase sets the RepeatBase and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithRepeatBase(repeatBase []int) ParametersLiteral[T] {
	p.RepeatBase = repeatBase
	return p
}

// WithExtendedCoeffsCount sets the ExtendedCoeffsCount and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithExtendedCoeffsCount(extendedCoeffsCount []int) ParametersLiteral[T] {
	p.ExtendedCoeffsCount = extendedCoeffsCount
	return p
}

// WithTruncatedRepetitionParameters sets the TruncatedRepetitionParameters and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithTruncatedRepetitionParameters(truncatedRepetitionParameters []GadgetParametersLiteral[T]) ParametersLiteral[T] {
	p.TruncatedRepetitionParameters = truncatedRepetitionParameters
	return p
}

// WithCountLUTs sets the LUTsCount and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithCountLUTs(countLUTs int) ParametersLiteral[T] {
	p.CountLUTs = countLUTs
	return p
}

// WithFullDomain sets the FullDomain and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithFullDomain(fullDomain bool) ParametersLiteral[T] {
	p.FullDomain = fullDomain
	return p
}

// WithCountCancelSignLUTs sets the CountCancelSignLUTs and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithCountCancelSignLUTs(countCancelSignLUTs int) ParametersLiteral[T] {
	p.CountCancelSignLUTs = countCancelSignLUTs
	return p
}

// // WithLazyCancelSign sets the LazyCancelSign and returns the new ParametersLiteral
// func (p ParametersLiteral[T]) WithLazyCancelSign(lazyCancelSign bool) ParametersLiteral[T] {
// 	p.LazyCancelSign = lazyCancelSign
// 	return p
// }

func (p ParametersLiteral[T]) WithTargetRedundancyInExtraction(TargetRedundancyInExtraction int) ParametersLiteral[T] {
	p.TargetRedundancyInExtraction = TargetRedundancyInExtraction
	return p
}

// WithInputNoiseIsGaussian sets the InputNoiseIsGaussian and returns the new ParametersLiteral
func (p ParametersLiteral[T]) WithInputNoiseIsGaussian(InputNoiseIsGaussian bool) ParametersLiteral[T] {
	p.InputNoiseIsGaussian = InputNoiseIsGaussian
	return p
}

// Compile transforms ParametersLiteral to read-only Parameters.
// If there is any invalid parameter in the literal, it panics.
// Default parameters are guaranteed to be compiled without panics.
//
// # Warning
//
// This method performs only basic sanity checks.
// Just because a parameter compiles does not necessarily mean it is safe or correct.
// Unless you are a cryptographic expert, DO NOT set parameters by yourself;
// always use the default parameters provided.
func (p ParametersLiteral[T]) Compile() Parameters[T] {
	if p.LookUpTableSize == 0 {
		p.LookUpTableSize = p.PolyDegree
	}
	if p.BlockSize == 0 {
		p.BlockSize = 1
	}

	switch {
	case p.LWEDimension <= 0:
		panic("LWEDimension smaller than zero")
	case p.LWEDimension > p.GLWERank*p.PolyDegree:
		panic("LWEDimension larger than GLWEDimension")
	case p.GLWERank <= 0:
		panic("GLWERank smaller than zero")
	case p.LookUpTableSize < p.PolyDegree:
		panic("LookUpTableSize smaller than PolyDegree")
	case p.LWEStdDev <= 0:
		panic("LWEStdDev smaller than zero")
	case p.GLWEStdDev <= 0:
		panic("GLWEStdDev smaller than zero")
	case p.BlockSize <= 0:
		panic("BlockSize smaller than zero")
	case p.LWEDimension%p.BlockSize != 0:
		panic("LWEDimension not multiple of BlockSize")
	case p.LookUpTableSize%p.PolyDegree != 0:
		panic("LookUpTableSize not multiple of PolyDegree")
	case !num.IsPowerOfTwo(p.PolyDegree):
		panic("PolyDegree not power of two")
	case !(p.BootstrapOrder == OrderKeySwitchBlindRotate || p.BootstrapOrder == OrderBlindRotateKeySwitch):
		panic("BootstrapOrder not valid")
	case p.BlockSize > 1 && p.MetaFBS:
		panic("Should use dense secret in Meta-FBS")
	case p.LookUpTableSize > p.PolyDegree && p.MetaFBS:
		panic("Should not use extended polynomials in Meta-FBS")
	}

	params := Parameters[T]{
		lweDimension:     p.LWEDimension,
		glweDimension:    p.GLWERank * p.PolyDegree,
		glweRank:         p.GLWERank,
		polyDegree:       p.PolyDegree,
		logPolyDegree:    num.Log2(p.PolyDegree),
		lookUpTableSize:  p.LookUpTableSize,
		polyExtendFactor: p.LookUpTableSize / p.PolyDegree,

		lweStdDev:  p.LWEStdDev,
		glweStdDev: p.GLWEStdDev,

		blockSize:  p.BlockSize,
		blockCount: p.LWEDimension / p.BlockSize,

		messageModulus: p.MessageModulus,
		scale:          num.DivRound(1<<(num.SizeT[T]()-1), p.MessageModulus),

		logQ:   num.SizeT[T](),
		floatQ: math.Exp2(float64(num.SizeT[T]())),

		blindRotateParameters: p.BlindRotateParameters.Compile(),
		keySwitchParameters:   p.KeySwitchParameters.Compile(),

		bootstrapOrder: p.BootstrapOrder,

		worstCaseLogFailureProb: p.WorstCaseLogFailureProb,
		fullTorus:               p.FullTorus,
		metaFBS:                 p.MetaFBS,
		TruncRepeatParameters: TruncRepeatParameters[T]{
			itersCount:          p.ItersCount,
			repeatBase:          p.RepeatBase,
			truncationBound:     p.TruncationBound,
			extendedCoeffsCount: p.ExtendedCoeffsCount},
		countLUTs:           max(int(NextPowerOfTwo(uint(p.CountLUTs))), 1),
		fullDomain:          p.FullDomain,
		countCancelSignLUTs: max((p.CountCancelSignLUTs), 1),
		// lazyCancelSign:       p.LazyCancelSign,
		targetRedundancyInExtraction:     p.TargetRedundancyInExtraction,
		inputNoiseIsGaussian:             p.InputNoiseIsGaussian,
		isDummyPublicFunctionalKeySwitch: p.IsDummyPublicFunctionalKeySwitch,
		RandomizedBlindRotate:            p.MetaFBS,
	}
	if p.FullDomain {
		params.countLUTs = max(params.countLUTs, 2)
	}
	params.truncatedRepetitionParameters = make([]GadgetParameters[T], len(p.TruncatedRepetitionParameters))
	for i := range p.TruncatedRepetitionParameters {
		params.truncatedRepetitionParameters[i] = p.TruncatedRepetitionParameters[i].Compile()
	}
	if p.FullTorus {
		params.scale *= 2 //can be lossy for non-power-of-two p
	}

	minDegree := p.MessageModulus
	if p.FullTorus {
		minDegree /= 2
	}
	if p.MetaFBS {
		minDegree *= T(params.countLUTs)
	}
	if minDegree > T(p.PolyDegree) {
		panic("poly degree too small")
	}

	return params
}

type TruncRepeatParameters[T TorusInt] struct {
	// itersCount is the number of truncRepeat iterations in a Meta-FBS
	itersCount int

	// LWE-to-RLWE packing is also realized through two truncRepeats
	//
	// the first one increases the redundancy from 1 to the desired value
	//
	// the second one performs a truncation and increases the encoding gap to countCancelSignLUTs
	//
	// in Meta-FDFB, repeatBase, extendedCoeffsCount, truncatedRepetitionParameters
	// will have a length of itersCount + 2, with the last two entries reserved for packing,
	// while redundancy will have a length of itersCount + 3

	// repeatBase is the factor by which the exponent is upscaled during the truncated repetitions
	repeatBase []int

	// truncationBound is the number of coefficients to keep during the truncated repetitions
	truncationBound []int

	// extendedCoeffsCount is the number of extended (garbage) coefficients during the truncated repetitions
	extendedCoeffsCount []int

	// truncatedRepetitionParameters is the gadget parameters for the truncated repetitions
	truncatedRepetitionParameters []GadgetParameters[T]
	// redundancy[i] is the redundancy before the i-th truncRepeat
	//
	// the redundancy after the last truncRepeat is also recorded as the last element of redundancy
	//
	// this is useful for centering the exponent in truncRepeat
	redundancy []int

	// amplify[i] is the the amplification factor applied to the noise in LWE ciphertext
	// before the i-th truncRepeat
	//
	// amplify[0] = 2N/p, amplify[i+1] = amplify[i]*repeatBase[i]
	//
	// this is needed by truncRepeat in Meta-FBS (single- and multi- value)
	amplify []int

	// mvGap[i] is the distance between two consecutive LUT entries in MV-BTS
	// before the i-th truncRepeat
	//
	// mvGap[0] = redundancy[0], mvGap[i+1] = mvGap[i]*repeatBase[i]
	//
	// this is needed by truncRepeat in multi-value Meta-FBS
	mvGap []int
}

func (trp TruncRepeatParameters[T]) Copy() TruncRepeatParameters[T] {
	return TruncRepeatParameters[T]{
		itersCount:                    trp.itersCount,
		repeatBase:                    append([]int{}, trp.repeatBase...),
		truncationBound:               append([]int{}, trp.truncationBound...),
		extendedCoeffsCount:           append([]int{}, trp.extendedCoeffsCount...),
		truncatedRepetitionParameters: append([]GadgetParameters[T]{}, trp.truncatedRepetitionParameters...),
		redundancy:                    append([]int{}, trp.redundancy...),
		amplify:                       append([]int{}, trp.amplify...),
		mvGap:                         append([]int{}, trp.mvGap...),
	}
}

// Parameters are read-only, compiled parameters based on ParametersLiteral.
type Parameters[T TorusInt] struct {
	// LWEDimension is the dimension of LWE lattice used. Usually this is denoted by n.
	lweDimension int
	// GLWEDimension is the dimension of GLWE lattice used, which is GLWERank * PolyDegree.
	glweDimension int
	// GLWERank is the rank of GLWE lattice used. Usually this is denoted by k.
	// Length of GLWE secret key is GLWERank, and length of GLWE ciphertext is GLWERank+1.
	glweRank int
	// PolyDegree is the degree of polynomials in GLWE entities. Usually this is denoted by N.
	polyDegree int
	// LogPolyDegree equals log(PolyDegree).
	logPolyDegree int
	// LookUpTableSize is the size of Lookup Table used in Blind Rotation.
	lookUpTableSize int
	// PolyExtendFactor equals LookUpTableSize / PolyDegree.
	polyExtendFactor int

	// LWEStdDev is the normalized standard deviation used for gaussian error sampling in LWE encryption.
	lweStdDev float64
	// GLWEStdDev is the normalized standard deviation used for gaussian error sampling in GLWE encryption.
	glweStdDev float64

	// BlockSize is the size of block to be used for LWE key sampling.
	blockSize int
	// BlockCount is a number of blocks in LWESecretkey. Equal to LWEDimension / BlockSize.
	blockCount int

	// MessageModulus is the modulus of the encoded message.
	messageModulus T
	// Scale is the scaling factor used for message encoding.
	// The lower log(Scale) bits are reserved for errors.
	// NOTE: when representing the noisy message as T, scale = cardinality(T) / (2p)
	scale T

	// logQ is the value of log(Q), where Q is the modulus of the ciphertext.
	logQ int
	// floatQ is the value of Q as float64.
	floatQ float64

	// blindRotateParameters is the gadget parameters for Blind Rotation.
	blindRotateParameters GadgetParameters[T]
	// keySwitchParameters is the gadget parameters for KeySwitching.
	keySwitchParameters GadgetParameters[T]

	// bootstrapOrder is the order of Programmable Bootstrapping.
	bootstrapOrder BootstrapOrder

	// worstCaseLogFailureProb is the Log2 per-event failure probability for estimating error bounds
	worstCaseLogFailureProb int

	// fullTorus indicates if the highest plaintext bit stores message or is left zero
	fullTorus bool

	// metaFBS indicates if meta functional bootstrap is used
	metaFBS bool

	TruncRepeatParameters[T]

	// countLUTs is the number of evaluated LUTs in a single bootstrap
	countLUTs int

	// fullDomain == true to use full domain functional bootstrap
	fullDomain bool

	// countCancelSignLUTs is the number of LUTs in multi-value FDFB-CancelSign
	//
	// countCancelSignLUTs equals 1 in a single-value Meta-FDFB,
	//
	// but can be greater than 1 in multi-value Meta-FDFB
	countCancelSignLUTs int

	targetRedundancyInExtraction int

	// // lazyCancelSign == true to CancelSign after gadget-product with integers in Meta-WoPPBSManyLUTs
	// lazyCancelSign bool

	// inputNoiseIsGaussian == true means the input noise can be regarded as a centered Gaussian
	inputNoiseIsGaussian bool

	isDummyPublicFunctionalKeySwitch bool

	// RandomizedBlindRotate is enabled for all Meta-PBS parameters.
	// The proof-of-concept implementation borrows an Encryptor as its uniform random source.
	RandomizedBlindRotate bool
}

// DefaultLWEDimension returns the default dimension for LWE entities.
// Returns LWEDimension if BootstrapOrder is OrderBlindRotateKeySwitch,
// and GLWEDimension otherwise.
func (p Parameters[T]) DefaultLWEDimension() int {
	if p.bootstrapOrder == OrderBlindRotateKeySwitch {
		return p.lweDimension
	}
	return p.glweDimension
}

// LWEDimension is the dimension of LWE lattice used. Usually this is denoted by n.
func (p Parameters[T]) LWEDimension() int {
	return p.lweDimension
}

// GLWEDimension is the dimension of GLWE lattice used, which is GLWERank * PolyDegree.
func (p Parameters[T]) GLWEDimension() int {
	return p.glweDimension
}

// GLWERank is the dimension of GLWE lattice used. Usually this is denoted by k.
// Length of GLWE secret key is GLWERank, and length of GLWE ciphertext is GLWERank+1.
func (p Parameters[T]) GLWERank() int {
	return p.glweRank
}

// PolyDegree is the degree of polynomials in GLWE entities. Usually this is denoted by N.
func (p Parameters[T]) PolyDegree() int {
	return p.polyDegree
}

// LogPolyDegree equals log(PolyDegree).
func (p Parameters[T]) LogPolyDegree() int {
	return p.logPolyDegree
}

// LookUpTableSize is the size of LookUpTable used in Blind Rotation.
func (p Parameters[T]) LookUpTableSize() int {
	return p.lookUpTableSize
}

// PolyExtendFactor returns LookUpTableSize / PolyDegree.
func (p Parameters[T]) PolyExtendFactor() int {
	return p.polyExtendFactor
}

// DefaultLWEStdDev returns the default standard deviation for LWE entities.
// Returns LWEStdDev if BootstrapOrder is OrderBlindRotateKeySwitch,
// and GLWEStdDev otherwise.
//
// This is a normlized standard deviation.
// For actual sampling, use [Parameters.DefaultLWEStdDevQ].
func (p Parameters[T]) DefaultLWEStdDev() float64 {
	if p.bootstrapOrder == OrderBlindRotateKeySwitch {
		return p.lweStdDev
	}
	return p.glweStdDev
}

// DefaultLWEStdDevQ returns DefaultLWEStdDev * Q.
func (p Parameters[T]) DefaultLWEStdDevQ() float64 {
	if p.bootstrapOrder == OrderBlindRotateKeySwitch {
		return p.lweStdDev * p.floatQ
	}
	return p.glweStdDev * p.floatQ
}

// LWEStdDev is the standard deviation used for gaussian error sampling in LWE encryption.
//
// This is a normlized standard deviation.
// For actual sampling, use [Parameters.LWEStdDevQ].
func (p Parameters[T]) LWEStdDev() float64 {
	return p.lweStdDev
}

// LWEStdDevQ returns LWEStdDev * Q.
func (p Parameters[T]) LWEStdDevQ() float64 {
	return p.lweStdDev * p.floatQ
}

// GLWEStdDev is the standard deviation used for gaussian error sampling in GLWE encryption.
//
// This is a normlized standard deviation.
// For actual sampling, use [Parameters.GLWEStdDevQ].
func (p Parameters[T]) GLWEStdDev() float64 {
	return p.glweStdDev
}

// GLWEStdDevQ returns GLWEStdDev * Q.
func (p Parameters[T]) GLWEStdDevQ() float64 {
	return p.glweStdDev * p.floatQ
}

// BlockSize is the size of block to be used for LWE key sampling.
func (p Parameters[T]) BlockSize() int {
	return p.blockSize
}

// BlockCount is a number of blocks in LWESecretkey. Equal to LWEDimension / BlockSize.
func (p Parameters[T]) BlockCount() int {
	return p.blockCount
}

// Scale is the scaling factor used for message encoding.
// The lower log(Scale) bits are reserved for errors.
func (p Parameters[T]) Scale() T {
	return p.scale
}

// MessageModulus is the modulus of the encoded message.
func (p Parameters[T]) MessageModulus() T {
	return p.messageModulus
}

// LogQ is the value of log(Q), where Q is the modulus of the ciphertext.
func (p Parameters[T]) LogQ() int {
	return p.logQ
}

// BlindRotateParameters is the gadget parameters for Programmable Bootstrapping.
func (p Parameters[T]) BlindRotateParameters() GadgetParameters[T] {
	return p.blindRotateParameters
}

// KeySwitchParameters is the gadget parameters for KeySwitching.
func (p Parameters[T]) KeySwitchParameters() GadgetParameters[T] {
	return p.keySwitchParameters
}

// BootstrapOrder is the order of Programmable Bootstrapping.
func (p Parameters[T]) BootstrapOrder() BootstrapOrder {
	return p.bootstrapOrder
}

// WorstCaseLogFailureProb returns the Log2 per-event failure probability used for Gaussian error bounds.
func (p Parameters[T]) WorstCaseLogFailureProb() int {
	return p.worstCaseLogFailureProb
}

// FullTorus indicates if the highest plaintext bit stores message or is left zero
func (p Parameters[T]) FullTorus() bool {
	return p.fullTorus
}

// metaFBS indicates if meta functional bootstrap is used
func (p Parameters[T]) MetaFBS() bool {
	return p.metaFBS
}

// itersCount is the number of blind rotations in a Meta-FBS
func (p Parameters[T]) ItersCount() int {
	return p.itersCount
}

// repeatBase is the factor by which the exponent is upscaled during the truncated repetitions
func (p Parameters[T]) RepeatBase() []int {
	return p.repeatBase
}

// truncationBound is the number of coefficients to keep during the truncated repetitions
func (p Parameters[T]) TruncationBound() []int {
	return p.truncationBound
}

// extendedCoeffsCount is the number of extended (garbage) coefficients during the truncated repetitions
func (p Parameters[T]) ExtendedCoeffsCount() []int {
	return p.extendedCoeffsCount
}

// truncatedRepetitionParameters is the gadget parameters for the truncated repetitions
func (p Parameters[T]) TruncatedRepetitionParameters() []GadgetParameters[T] {
	return p.truncatedRepetitionParameters
}

// CountLUTs is the number of LUTs evaluated in a single bootstrap
func (p Parameters[T]) CountLUTs() int {
	return p.countLUTs
}

// FullDomain indicates if FDFB is used
func (p Parameters[T]) FullDomain() bool {
	return p.fullDomain
}

// CountCancelSignLUTs is the number of LUTs in the multi-value FDFB-CancelSign used in Meta-FDFB
func (p Parameters[T]) CountCancelSignLUTs() int {
	return p.countCancelSignLUTs
}

func (p Parameters[T]) TargetRedundancyInExtraction() int {
	return p.targetRedundancyInExtraction
}

// // LazyCancelSign indicates if CancelSign is performed after the scalar gadget product
// func (p Parameters[T]) LazyCancelSign() bool {
// 	return p.lazyCancelSign
// }

// InputNoiseIsGaussian indicates if the input noise can be regarded as a centered Gaussian
func (p Parameters[T]) InputNoiseIsGaussian() bool {
	return p.inputNoiseIsGaussian
}

// CountTruncRepeats returns the number of truncRepeats that an output ciphertext went through
func (p Parameters[T]) CountTruncRepeats() int {
	if !p.metaFBS {
		return 0
	}
	if !p.fullDomain {
		return p.itersCount
	}
	return p.itersCount + 1
}

// CountBlindRotations returns the number of blind rotations that an output ciphertext went through
func (p Parameters[T]) CountBlindRotations() int {
	if !p.metaFBS {
		return 1
	}
	if !p.fullDomain {
		return p.itersCount + 1
	}
	return p.itersCount + 1 + (p.countLUTs-1+p.countCancelSignLUTs-1)/p.countCancelSignLUTs
}

// IsPublicKeyEncryptable returns true if public key encryption is supported.
//
// Currently, public key encryption is supported only with BootstrapOrder OrderKeySwitchBlindRotate.
func (p Parameters[T]) IsPublicKeyEncryptable() bool {
	return p.bootstrapOrder == OrderKeySwitchBlindRotate
}

// Literal returns a ParametersLiteral from this Parameters.
func (p Parameters[T]) Literal() ParametersLiteral[T] {
	ret := ParametersLiteral[T]{
		LWEDimension:    p.lweDimension,
		GLWERank:        p.glweRank,
		PolyDegree:      p.polyDegree,
		LookUpTableSize: p.lookUpTableSize,

		LWEStdDev:  p.lweStdDev,
		GLWEStdDev: p.glweStdDev,

		BlockSize: p.blockSize,

		MessageModulus: p.messageModulus,

		BlindRotateParameters: p.blindRotateParameters.Literal(),
		KeySwitchParameters:   p.keySwitchParameters.Literal(),

		BootstrapOrder: p.bootstrapOrder,

		WorstCaseLogFailureProb:      p.worstCaseLogFailureProb,
		FullTorus:                    p.fullTorus,
		MetaFBS:                      p.metaFBS,
		ItersCount:                   p.itersCount,
		RepeatBase:                   p.repeatBase,
		TruncationBound:              p.truncationBound,
		ExtendedCoeffsCount:          p.extendedCoeffsCount,
		CountLUTs:                    p.countLUTs,
		FullDomain:                   p.fullDomain,
		CountCancelSignLUTs:          p.countCancelSignLUTs,
		TargetRedundancyInExtraction: p.targetRedundancyInExtraction,
		// LazyCancelSign:          p.lazyCancelSign,
		InputNoiseIsGaussian: p.inputNoiseIsGaussian,
	}
	ret.TruncatedRepetitionParameters = make([]GadgetParametersLiteral[T], len(p.truncatedRepetitionParameters))
	for i := range p.truncatedRepetitionParameters {
		ret.TruncatedRepetitionParameters[i] = p.truncatedRepetitionParameters[i].Literal()
	}
	return ret
}

// GadgetFuncLogBasesAssign returns a list of log(gadget bases) (from high to low) used for decomposing an LUT
func (param Parameters[T]) GadgetFuncLogBasesAssign(gadgetLength int, logGadgetBases []int) {
	p := param.messageModulus
	if !param.fullTorus {
		p *= 2
	}
	totalBits := bits.Len(uint(p)) - 1
	minBits := totalBits / gadgetLength
	extraBits := totalBits - gadgetLength*minBits
	logGadgetBases = logGadgetBases[:gadgetLength]
	for i := range gadgetLength {
		if i < extraBits {
			logGadgetBases[i] = minBits + 1
		} else {
			logGadgetBases[i] = minBits
		}
	}
}

// CapacityForGadgetMult returns the capacity bits required to perform a gadget multiplication
func (param Parameters[T]) CapacityForGadgetMultAssign(gadgetLength int, logGadgetBases []int) float64 {
	param.GadgetFuncLogBasesAssign(gadgetLength, logGadgetBases)
	capacity := 0.0
	for i := range gadgetLength {
		capacity += math.Pow(4, float64(logGadgetBases[i])-1)
	}
	return math.Log2(math.Sqrt(capacity))
}

// EstimateHwtLWE returns an estimated Hamming weight of the LWE secret
//
// the return value is blockSize/(blockSize+1) * blockCount, which is equal to n/2 for dense secret
func (p Parameters[T]) EstimateHwtLWE() (Hwt float64) {
	blockCount := float64(p.blockCount)
	blockSize := float64(p.blockSize)
	P := blockSize / (blockSize + 1)
	return blockCount * P
	// Erfcinv(2^worstCaseLogFailureProb) * sqrt(2) * stddevHwt + meanHwt
	// NOTE: below are code for worst case Hamming weight estimation
	// Bernoulli distribution with parameter (P, blockCount)
	// meanHwt := blockCount * P
	// stddevHwt := math.Sqrt(blockCount * P * (1 - P))
	// Hwt = meanHwt + GaussianBoundForFailureProb(p.worstCaseLogFailureProb)*stddevHwt
	// return math.Ceil(Hwt)
}

// EstimateHwtExtraGLWE returns an estimated Hamming weight of the extra part in GLWE secret
//
// the return value is E(||extra GLWE secret||^2) to be used in the average-case analysis
func (p Parameters[T]) EstimateHwtExtraGLWE() (Hwt float64) {
	n := float64(p.lweDimension)
	k := float64(p.glweRank)
	N := float64(p.polyDegree)
	GLWEExtraDim := N*k - n
	return GLWEExtraDim / 2
	// NOTE: below are code for worst case Hamming weight estimation
	// meanHwt := GLWEExtraDim / 2
	// stddevHwt := math.Sqrt(GLWEExtraDim * 0.25)
	// // Erfcinv(2^worstCaseLogFailureProb) * sqrt(2) * stddevHwt + meanHwt
	// // native Erfcinv in go does provide enough precision, thus is not used here
	// Hwt = meanHwt + GaussianBoundForFailureProb(p.worstCaseLogFailureProb)*stddevHwt
	// return math.Ceil(Hwt)
}

// EstimateHwtGLWE returns an estimated Hamming weight of the GLWE secret
//
// the return value is E(||GLWE secret||^2) to be used in the average-case analysis
func (p Parameters[T]) EstimateHwtGLWE() (Hwt float64) {
	blockCount := float64(p.blockCount)
	blockSize := float64(p.blockSize)
	P := blockSize / (blockSize + 1)
	n := float64(p.lweDimension)
	k := float64(p.glweRank)
	N := float64(p.polyDegree)
	GLWEExtraDim := N*k - n
	return GLWEExtraDim/2 + blockCount*P
	// NOTE: below are code for worst case Hamming weight estimation
	// meanHwt := GLWEExtraDim/2 + blockCount*P
	// stddevHwt := math.Sqrt(GLWEExtraDim*0.25 + blockCount*P*(1-P))
	// // Erfcinv(2^worstCaseLogFailureProb) * sqrt(2) * stddevHwt + meanHwt
	// Hwt = meanHwt + GaussianBoundForFailureProb(p.worstCaseLogFailureProb)*stddevHwt
	// return math.Ceil(Hwt)
}

// EstimateModSwitchStdDev returns an estimated standard deviation of error from modulus switching.
//
// The modulus switching has a target modulus of 2N*extDegree = 2*lookUpTableSize
//
// The noise variance is measured by normalizing the modulus from 2*lookUpTableSize to q=2^bits(T)
func (p Parameters[T]) EstimateModSwitchStdDev() float64 {
	L := float64(p.lookUpTableSize)
	q := p.floatQ

	h := p.EstimateHwtLWE()

	modSwitchVar := ((h + 1) * q * q) / (48 * L * L)
	if p.blockSize <= 1 {
		// use CLOT21
		n := float64(p.lweDimension)
		w := 2 * L
		modSwitchVar = q*q/(w*w)*(n/2+1)/12 - 1.0/12 + n/48
	}

	return math.Sqrt(modSwitchVar)
}

// EstimateOverflowStdDev returns an estimated standard deviation of the q-overflow of a mod-q GLWE ciphertext
// with q sufficiently large
func (p Parameters[T]) EstimateOverflowStdDev() float64 {
	// (n/2+2)/12
	h := p.EstimateHwtLWE()
	return math.Sqrt((h + 2) / 12)
}

// EstimateBlindRotateStdDev returns an estimated standard deviation of error from Blind Rotation.
//
// The noise variance is measured by normalizing the modulus from 2*lookUpTableSize to q=2^bits(T)
func (p Parameters[T]) EstimateBlindRotateStdDev() float64 {
	n := float64(p.lweDimension)
	k := float64(p.glweRank)
	N := float64(p.polyDegree)
	beta := p.GLWEStdDevQ()
	q := p.floatQ

	h := p.EstimateHwtLWE()
	H := p.EstimateHwtGLWE()

	Bbr := float64(p.blindRotateParameters.Base())
	Lbr := float64(p.blindRotateParameters.Level())

	if p.blockSize <= 1 {
		// just use CLOT21 for dense keys
		var1, var2, var3 := n*Lbr*(k+1)*N*(Bbr*Bbr+2)/12*beta*beta,
			n*(q*q/(24*math.Pow(Bbr, 2*Lbr))-1.0/12)*(1+k*N/2)+n*k*N/32+n/16*math.Pow(1-k*N/2, 2),
			n*math.Exp2(-108.6)*(k+1)*N*N*(q*q)*Lbr*(Bbr*Bbr)
		varBr := var1 + var2 + var3
		return math.Sqrt(varBr)
	}

	originalFactor := 1.0
	if p.blockSize <= 1 {
		originalFactor = 0.5
	}

	// NOTE: error variance from decomposition residue
	// decomposition err: centered uniform with radius 1/2*B^-L mod 1 -> var = q^2/(12*B^(2L)) mod q
	// iter count: blockCount with nonzero RGSW ptxt = h
	// ring mult factor: Hwt of GLWE + 1 ~= h + (kN-n)/2 + 1 -> H + 1
	// inf norm of nonzero RGSW ptxt = 2 * originalFactor
	// Total var = h(h+(kN-n)/2+1)q^2/(6b^(2L))
	blindRotateVar1 := h * (H + 1) * (q * q) / (6 * math.Pow(Bbr, 2*Lbr)) * originalFactor
	// NOTE: error variance from RGSW noise
	// RGSW noise var: 2 * originalFactor * beta^2 * blockSize (q is included in beta)
	// decomposed parts var: 1/12 * B^2
	// ring mult factor: N
	// gadget length: L*(k+1)
	// iter count: blockCount
	// Total var = n(L(k+1)N*beta^2*B^2)/6
	blindRotateVar2 := originalFactor * n * (Lbr * (k + 1) * N * beta * beta * Bbr * Bbr) / 6
	// NOTE: error variance from integer->double rounding in RGSW (?)
	// 2*originalFactor*nNL(k+1)B^2q^2 is the external product noise amplification factor normalized from mod 1 to mod q, similar to the previous noise variance
	// h + (k*N-n)/2 + 1 is the ring mult factor -> H + 1
	// 2^-108.6 * 2 seems to be the noise variance in each component of RGSW ciphertexts
	blindRotateFFTVar := n * math.Exp2(-108.6) * (k + 1) * (H + 1) * N * (q * q) * Lbr * (Bbr * Bbr) * 2 * 2 * originalFactor
	// NOTE: output error variance of blind rotation
	blindRotateVar := blindRotateVar1 + blindRotateVar2 + blindRotateFFTVar

	debugf("stddev from decomp, RGSW, FFT = 2^%f, 2^%f, 2^%f\n",
		math.Log2(math.Sqrt(blindRotateVar1)/q),
		math.Log2(math.Sqrt(blindRotateVar2)/q),
		math.Log2(math.Sqrt(blindRotateFFTVar)/q))
	return math.Sqrt(blindRotateVar)
}

// MinimizeBlindRotateVarianceBbr returns the Bbr that minimized the bilnd rotation variance
func (p Parameters[T]) MinimizeBlindRotateVarianceBbr() float64 {
	n := float64(p.lweDimension)
	k := float64(p.glweRank)
	N := float64(p.polyDegree)
	beta := p.GLWEStdDevQ()
	q := p.floatQ

	h := p.EstimateHwtLWE()
	H := p.EstimateHwtGLWE()

	// Bbr := float64(p.blindRotateParameters.Base())
	Lbr := float64(p.blindRotateParameters.Level())

	originalFactor := 1.0
	if p.blockSize <= 1 {
		originalFactor = 0.5
	}

	// let X=Bbr^2, express var=f(X)=AX+BX^{-L}
	varFactorB := h * (H + 1) * (q * q) / 6 * originalFactor
	varFactorA := n*(Lbr*(k+1)*N*beta*beta)/6*originalFactor +
		n*math.Exp2(-108.6)*(k+1)*(H+1)*N*(q*q)*Lbr*2*2*originalFactor

	if p.blockSize <= 1 {
		// just use CLOT21 for dense keys
		varFactorA = n*Lbr*(k+1)*N/12*beta*beta + n*math.Exp2(-108.6)*(k+1)*N*N*(q*q)*Lbr
		varFactorB = n * q * q / 24 * (1 + k*N/2)
	}
	// f'(X)=A-BLX^{-L-1}=0
	// Bbr^2=X=(A/BL)^{-1/(L+1)}
	return math.Pow(varFactorA/varFactorB/Lbr, -1/(Lbr+1)/2)
}

// EstimateKeySwitchForBootstrapStdDev returns an estimated standard deviation of error from Key Switching for bootstrapping.
//
// The noise variance is measured by normalizing the modulus from 2*lookUpTableSize to q=2^bits(T)
func (p Parameters[T]) EstimateKeySwitchForBootstrapStdDev() float64 {
	n := float64(p.lweDimension)
	k := float64(p.glweRank)
	N := float64(p.polyDegree)
	alpha := p.LWEStdDevQ()
	q := p.floatQ
	Hextra := p.EstimateHwtExtraGLWE()

	Bks := float64(p.keySwitchParameters.Base())
	Lks := float64(p.keySwitchParameters.Level())

	if p.blockSize <= 1 {
		// use CLOT21
		varKs := Lks*(k*N-n)*(alpha*alpha)*(Bks*Bks+2)/12 +
			(q*q/(12*math.Pow(Bks, 2*Lks))-1.0/12)*(k*N-n)/2 + (k*N-n)/16
		return math.Sqrt(varKs)
	}

	// NOTE: error variance from gadget decomposition residue
	// Hwt of the extra GLWE secret: (kN-n)/2 -> Hextra
	// residue variance: q^2*1/(12*B^2L)
	keySwitchVar1 := Hextra * (q * q) / (12 * math.Pow(Bks, 2*Lks))
	// NOTE: error variance from KSK noise
	// KSK count: kN-n
	// error var in each KSK: alpha^2*L*B^2/12, q is included in alpha
	keySwitchVar2 := (k*N - n) * (alpha * alpha * Lks * Bks * Bks) / 12
	// NOTE: variance of the key switching error
	keySwitchVar := keySwitchVar1 + keySwitchVar2
	// we don't have FFTvar here because all computation is done on integers

	return math.Sqrt(keySwitchVar)
}

// MinimizeKeySwitchForBootstrapVarianceBks returns the Bks that minimized the key switching variance.
func (p Parameters[T]) MinimizeKeySwitchForBootstrapVarianceBks() float64 {
	n := float64(p.lweDimension)
	k := float64(p.glweRank)
	N := float64(p.polyDegree)
	alpha := p.LWEStdDevQ()
	q := p.floatQ
	Hextra := p.EstimateHwtExtraGLWE()

	Lks := float64(p.keySwitchParameters.Level())

	// X=Bks^2, Var=f(X)=AX+BX^{-L}
	varFactorB := Hextra * (q * q) / 12
	varFactorA := (k*N - n) * (alpha * alpha * Lks) / 12

	if p.blockSize <= 1 {
		// use CLOT21
		varFactorA = Lks * (k*N - n) * (alpha * alpha) / 12
		varFactorB = q * q / 12 * (k*N - n) / 2
	}

	// f'(X)=A-BLX^{-L-1}=0
	// Bbr^2=X=(A/BL)^{-1/(L+1)}
	return math.Pow(varFactorA/varFactorB/Lks, -1/(Lks+1)/2)
}

// truncRepeatNoiseFactor returns N + (b-a)ceil(N/(epsilon+1)).
func (p Parameters[T]) truncRepeatNoiseFactor(i int) float64 {
	N := p.polyDegree
	trkCount := (N + p.extendedCoeffsCount[i]) / (p.extendedCoeffsCount[i] + 1)
	bMinusA := 2 * p.truncationBound[i]
	if i != p.itersCount {
		bMinusA += (p.countLUTs - 1) * p.mvGap[i]
	}
	return float64(N + bMinusA*trkCount)
}

func (p Parameters[T]) maxCancelSignBatchSize() int {
	if !p.fullDomain {
		return 1
	}
	return min(p.countCancelSignLUTs, p.countLUTs-1)
}

// EstimateAllTruncRepeatStdDev returns the worst-case standard deviation from all TruncRepeat calls.
func (p Parameters[T]) EstimateAllTruncRepeatStdDev() float64 {
	return p.estimateAllTruncRepeatStdDev(p.maxCancelSignBatchSize())
}

func (p Parameters[T]) estimateAllTruncRepeatStdDev(cancelSignBatchSize int) (stddev float64) {
	if !p.metaFBS {
		return 0
	}
	N := float64(p.polyDegree)
	q := p.floatQ
	beta := p.GLWEStdDevQ()
	H := p.EstimateHwtGLWE()

	iters := p.CountTruncRepeats()
	for i := range iters {
		Btr := float64(p.truncatedRepetitionParameters[i].Base())
		Ltr := float64(p.truncatedRepetitionParameters[i].Level())

		if p.blockSize <= 1 {
			// follow CLOT21
			factor := p.truncRepeatNoiseFactor(i)
			decompResidueVar := (q*q/(12*math.Pow(Btr, 2*Ltr))-1.0/12)*N/2 + N/16
			vEmp := Ltr * factor * (Btr*Btr + 2) * (beta*beta/12 + N*math.Exp2(19.4))
			if i == p.itersCount { // last tr in FDFB
				stddev += decompResidueVar + float64(cancelSignBatchSize)*vEmp
			} else {
				stddev += decompResidueVar + vEmp
			}
			continue
		}

		// d := p.truncationBound[i]
		// B := p.repeatBase[i]
		// e := p.extendedCoeffsCount[i]
		// trkCount := float64((N + e) / (e + 1)) // ceil(N/(e+1))
		// mvGap := p.mvGap[i]
		// truncSize := float64(2*d + e + 1 + mvGap*(countLUTs-1))

		// NOTE: decomposition residue variance
		// decomposition err: q^2/(12*Btr^(2*Ltr))
		// ring mult factor: H
		decompResidueVar := H * (q * q) / (12 * math.Pow(Btr, 2*Ltr))
		// NOTE: error variance from RGSW noise
		// decomposed parts var : 1/12 * Btr^2
		// gadget length: Ltr
		// ring mult factor N
		TrkVar := N * Ltr * Btr * Btr * beta * beta / 12
		// NOTE: FFT var
		// N * LB^2 * q^2
		// 2^-108.6 * 2, H
		FFTVar := H * Ltr * N * Btr * Btr * math.Exp2(-108.6) * 2 * q * q
		stddev += decompResidueVar + TrkVar + FFTVar
	}
	stddev = math.Sqrt(stddev)
	return
}

func (p Parameters[T]) MinimizeAllTruncRepeatVarianceBtr() (Btrs []float64) {
	if !p.metaFBS {
		return nil
	}
	N := float64(p.polyDegree)
	q := p.floatQ
	beta := p.GLWEStdDevQ()
	H := p.EstimateHwtGLWE()
	countCancelSignLUTs := p.maxCancelSignBatchSize()

	Btrs = make([]float64, p.CountTruncRepeats())
	for i := range Btrs {
		Ltr := float64(p.truncatedRepetitionParameters[i].Level())

		factor := p.truncRepeatNoiseFactor(i)

		// X=Btr^2, Var=f(X)=AX+BX^{-Ltr}
		varFactorB := H * (q * q) / 12
		varFactorA := factor * Ltr * (beta*beta/12 + N*math.Exp2(19.4))

		if i == p.itersCount { // last tr in FDFB
			varFactorA *= float64(countCancelSignLUTs)
		}
		// f'(X)=A-BLX^{-L-1}=0
		// Bbr^2=X=(A/BL)^{-1/(L+1)}
		Btrs[i] = math.Pow(varFactorA/varFactorB/Ltr, -1/(Ltr+1)/2)
	}
	return
}

// EstimateMaxErrorStdDev returns an estimated standard deviation of maximum possible error.
func (p Parameters[T]) EstimateMaxErrorStdDev() float64 {
	modSwitchStdDev := p.EstimateModSwitchStdDev()
	blindRotateStdDev := p.EstimateBlindRotateStdDev()
	keySwitchStdDev := p.EstimateKeySwitchForBootstrapStdDev()

	return math.Sqrt(modSwitchStdDev*modSwitchStdDev + blindRotateStdDev*blindRotateStdDev + keySwitchStdDev*keySwitchStdDev)
}

// EstimateFailureProbability returns the failure probability of bootstrapping.
func (p Parameters[T]) EstimateFailureProbability() float64 {
	bound := p.floatQ / (4 * float64(p.messageModulus))
	return math.Erfc(bound / (math.Sqrt2 * p.EstimateMaxErrorStdDev()))
}

// ByteSize returns the byte size of the parameters.
func (p Parameters[T]) ByteSize() int {
	return 8*8 + p.blindRotateParameters.ByteSize() + p.keySwitchParameters.ByteSize() + 1
}

// WriteTo implements the [io.WriterTo] interface.
//
// The encoded form is as follows:
//
//	[ 8] LWEDimension
//	[ 8] GLWERank
//	[ 8] PolyDegree
//	[ 8] LookUpTableSize
//	[ 8] LWEStdDev
//	[ 8] GLWEStdDev
//	[ 8] BlockSize
//	[ 8] MessageModulus
//	     BlindRotateParameters
//	     KeySwitchParameters
//	[ 1] BootstrapOrder
func (p Parameters[T]) WriteTo(w io.Writer) (n int64, err error) {
	var nWrite int
	var nWrite64 int64
	var buf [8]byte

	lweDimension := p.lweDimension
	binary.BigEndian.PutUint64(buf[:], uint64(lweDimension))
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	glweRank := p.glweRank
	binary.BigEndian.PutUint64(buf[:], uint64(glweRank))
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	polyDegree := p.polyDegree
	binary.BigEndian.PutUint64(buf[:], uint64(polyDegree))
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	lookUpTableSize := p.lookUpTableSize
	binary.BigEndian.PutUint64(buf[:], uint64(lookUpTableSize))
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	lweStdDev := math.Float64bits(p.lweStdDev)
	binary.BigEndian.PutUint64(buf[:], lweStdDev)
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	glweStdDev := math.Float64bits(p.glweStdDev)
	binary.BigEndian.PutUint64(buf[:], glweStdDev)
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	blockSize := p.blockSize
	binary.BigEndian.PutUint64(buf[:], uint64(blockSize))
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	messageModulus := uint64(p.messageModulus)
	binary.BigEndian.PutUint64(buf[:], messageModulus)
	if nWrite, err = w.Write(buf[:]); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	if nWrite64, err = p.blindRotateParameters.WriteTo(w); err != nil {
		return n + nWrite64, err
	}
	n += nWrite64

	if nWrite64, err = p.keySwitchParameters.WriteTo(w); err != nil {
		return n + nWrite64, err
	}
	n += nWrite64

	bootstrapOrder := p.bootstrapOrder
	if nWrite, err = w.Write([]byte{byte(bootstrapOrder)}); err != nil {
		return n + int64(nWrite), err
	}
	n += int64(nWrite)

	if n < int64(p.ByteSize()) {
		return n, io.ErrShortWrite
	}

	return
}

// ReadFrom implements the [io.ReaderFrom] interface.
func (p *Parameters[T]) ReadFrom(r io.Reader) (n int64, err error) {
	var nRead int
	var nRead64 int64
	var buf [8]byte

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	lweDimension := int(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	glweRank := int(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	polyDegree := int(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	lookUpTableSize := int(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	lweStdDev := math.Float64frombits(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	glweStdDev := math.Float64frombits(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	blockSize := int(binary.BigEndian.Uint64(buf[:]))

	if nRead, err = io.ReadFull(r, buf[:]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	messageModulus := T(binary.BigEndian.Uint64(buf[:]))

	var blindRotateParameters GadgetParameters[T]
	if nRead64, err = blindRotateParameters.ReadFrom(r); err != nil {
		return n + nRead64, err
	}
	n += nRead64

	var keySwitchParameters GadgetParameters[T]
	if nRead64, err = keySwitchParameters.ReadFrom(r); err != nil {
		return n + nRead64, err
	}
	n += nRead64

	if nRead, err = io.ReadFull(r, buf[:1]); err != nil {
		return n + int64(nRead), err
	}
	n += int64(nRead)
	bootstrapOrder := BootstrapOrder(buf[0])

	*p = ParametersLiteral[T]{
		LWEDimension:    lweDimension,
		GLWERank:        glweRank,
		PolyDegree:      polyDegree,
		LookUpTableSize: lookUpTableSize,

		LWEStdDev:  lweStdDev,
		GLWEStdDev: glweStdDev,

		BlockSize: blockSize,

		MessageModulus: messageModulus,

		BlindRotateParameters: blindRotateParameters.Literal(),
		KeySwitchParameters:   keySwitchParameters.Literal(),

		BootstrapOrder: bootstrapOrder,
	}.Compile()

	return
}

// MarshalBinary implements the [encoding.BinaryMarshaler] interface.
func (p Parameters[T]) MarshalBinary() (data []byte, err error) {
	buf := bytes.NewBuffer(make([]byte, 0, p.ByteSize()))
	_, err = p.WriteTo(buf)
	return buf.Bytes(), err
}

// UnmarshalBinary implements the [encoding.BinaryUnmarshaler] interface.
func (p *Parameters[T]) UnmarshalBinary(data []byte) error {
	buf := bytes.NewBuffer(data)
	_, err := p.ReadFrom(buf)
	return err
}

type SweepConfig struct {
	// CapacityBits is the number of bits reserved for homomorphic computation after SampleExtract
	CapacityBits float64
	// MaxGadgetLength is the maximum value when searching for Lbr, Lks and Ltr
	MaxGadgetLength int

	// CapacityBitsMeta is the number of bits reserved after keyswitch in Meta-FBS
	CapacityBitsMeta float64

	// For a more automatic parameter sweeping
	CapacityBitsMetaBegin, CapacityBitsMetaEnd, CapacityBitsMetaStep float64

	RequiredExtractionRedundancyBegin, RequiredExtractionRedundancyEnd int
}

func DefaultSweepConfig() SweepConfig {
	return SweepConfig{
		CapacityBits:     0.5, // one addition
		MaxGadgetLength:  12,
		CapacityBitsMeta: 0.5,
	}
}

func NextPowerOfTwo(n uint) uint {
	if n == 0 {
		return 0
	}
	return 1 << bits.Len(n-1)
}

func PrevPowerOfTwo(n uint) uint {
	if n == 0 {
		return 0
	}
	return 1 << (bits.Len(n) - 1)
}

// SweepParameter finds the fastest parameters that satisfies the requirements in config
//
// Only gadget parameters and Meta-FBS parameters are searched
func SweepParameter[T TorusInt](paramsLit ParametersLiteral[T], config SweepConfig) (params Parameters[T], err error) {
	params = paramsLit.Compile()
	// For Meta-FBS this is a per-perturbation bound; the caller reserves any union-bound margin.
	GaussianK := GaussianBoundForFailureProb(params.worstCaseLogFailureProb)
	capacityFactor := math.Pow(2, 2*config.CapacityBits)

	funcUpdateBase := func(gadget *GadgetParameters[T], base T) {
		if base < 2 {
			return
		}
		*gadget = gadget.Literal().WithBase(base).Compile()
	}
	// helper function that find the Bbr that minimizes output error
	funcBestBbr := func() float64 {
		Bbr := NextPowerOfTwo(uint(params.MinimizeBlindRotateVarianceBbr()))
		funcUpdateBase(&params.blindRotateParameters, T(Bbr))
		var1 := math.Pow(params.EstimateBlindRotateStdDev(), 2)
		funcUpdateBase(&params.blindRotateParameters, T(Bbr)>>1)
		var2 := math.Pow(params.EstimateBlindRotateStdDev(), 2)
		if var1 < var2 {
			funcUpdateBase(&params.blindRotateParameters, T(Bbr))
			return var1
		} else {
			return var2
		}
	}
	// helper function that finds the Bks minimizing output error
	funcBestBks := func() float64 {
		Bks := NextPowerOfTwo(uint(params.MinimizeKeySwitchForBootstrapVarianceBks()))
		funcUpdateBase(&params.keySwitchParameters, T(Bks))
		var1 := math.Pow(params.EstimateKeySwitchForBootstrapStdDev(), 2)
		funcUpdateBase(&params.keySwitchParameters, T(Bks)>>1)
		var2 := math.Pow(params.EstimateKeySwitchForBootstrapStdDev(), 2)
		if var1 < var2 {
			funcUpdateBase(&params.keySwitchParameters, T(Bks))
			return var1
		} else {
			return var2
		}
	}
	// Non META case
	if !params.MetaFBS() {
		maxVar := math.Pow(float64(params.scale)/2/GaussianK, 2) -
			math.Pow(params.EstimateModSwitchStdDev(), 2)
		maxBrVar := maxVar / capacityFactor
		// find the smallest Lbr satisfying BrVar < maxBrVar
		for Lbr := 1; Lbr <= config.MaxGadgetLength; Lbr++ {
			params.blindRotateParameters.level = Lbr
			curVar := funcBestBbr()
			if curVar < maxBrVar {
				break
			}
			if Lbr == config.MaxGadgetLength {
				return params, fmt.Errorf("failed to find Lbr")
			}
		}
		// find the smallest Lks satisfying KSVar < maxVar
		for Lks := 1; Lks <= config.MaxGadgetLength; Lks++ {
			params.keySwitchParameters.level = Lks
			curVar := funcBestBks()
			if curVar < maxVar {
				break
			}
			if Lks == config.MaxGadgetLength {
				return params, fmt.Errorf("failed to find Lks")
			}
		}
		// check the variance
		for {
			varBr := funcBestBbr()
			ksGadget := params.keySwitchParameters
			found := false
			if params.keySwitchParameters.level <= config.MaxGadgetLength {
				varKs := funcBestBks()
				if capacityFactor*varBr+varKs < maxVar {
					found = true
					break
				}
				params.keySwitchParameters.level++
			}
			if found {
				break
			}
			params.keySwitchParameters = ksGadget
			params.blindRotateParameters.level++
			if params.blindRotateParameters.level > config.MaxGadgetLength {
				return params, fmt.Errorf("failed to find gadget parameters")
			}
		}
		return params, nil
	}
	// META case
	//  (1) support PBSManyLUTs: OK
	//   	different from the regular approach where LUT = sum_i(X^i*subLUT_i)
	//   	we put the redundancy at the LSB for compatibility with fast truncRepeat
	//   	we still require redundancy >= 2*errBound+1, but truncate to
	// 	 	[-errBound-redundancy/2, errBound+redundancy/2+(countLUTs-1)*mvGap]
	//   	instead of [-errBound-redundancy/2, errBound+redundancy/2]
	//  (2) support FDFB: OK
	// 		1. use PBSManyLUTs as a subroutine
	// 		2. a better packing using truncRepeat
	//  (3) support EBS: truncRepeat needs some modifications // will not be implemented
	gaussianBound := func(variance, gaussianK float64) float64 {
		return math.Ceil(gaussianK*math.Sqrt(variance) + 0.5)
	}
	overflowVar := math.Pow(params.EstimateOverflowStdDev(), 2)
	overflowBound := gaussianBound(overflowVar, GaussianK)
	inputVar := math.Pow(math.Pow(2, -config.CapacityBitsMeta-1)/GaussianK, 2) // the error variance on the PLAINTEXT, i.e.,  (actual variance in uint64) / scale^2
	gaussianInput := params.InputNoiseIsGaussian()

	// Single-value bootstrap
	// In the i-th iteration,
	// 		redundancy(i) <= redundancy(0)*repeatBase[0]*...*repeatBase[i-1], redundancy(0) <= 2N/p = initRedundancy,
	//      amplify(i) = 2N/p*repeatBase[0]*...*repeatBase[i-1] >= redundancy(i)
	// 	the noise bound is
	// 		bound(i) = Ceil(GaussianK * Sqrt(overflowVar + amplify(i)^2 * inputVar) + 1/2), for Gaussian input noise
	//				 = overflowBound+Ceil(amplify(i)/2*2^{-capacityBitsMeta})       , for bounded input noise
	// SampleExtract is correct when redundancy(i) >= 2*bound(i)+1,
	// 	whose necessary but insufficient condition is
	//		For Gaussian input noise:
	// 			redundancy(i) >= 2*Ceil(GaussianK*Sqrt(overflowVar + redundancy(i)^2 * inputVar) + 1/2) + 1,
	//      	since 4*GaussianK^2*Vin = 2^-2*capBitsMeta < 1, the corresponding quadratic function is U-shaped
	//			also, the inequality is violated for redundancy(i)=0, meaning we need to take the right intersection point
	//		For bounded input noise:
	//			redundancy(i) >= (2*overflowBound+1)/(1 - 2^{-capacityBitsMeta})
	//
	//  the truncation bound is
	// 		truncBound(i) = bound(i)+floor(redundancy(i)/2)
	// repeatBase[i] * (2*truncBound(i) + 1 + extendedCoeffsCount[i]) <= N

	// PBSManyLUTs:
	// In the i-th iteration,
	//      initRedundancy = 2N/p (or N/p for WoPPBS)
	// 		redundancy(i) <= redundancy(0)*repeatBase[0]*...*repeatBase[i-1], redundancy(0) <= initRedundancy/countLUTs,
	//      amplify(i) = initRedundancy*repeatBase[0]*...*repeatBase[i-1] >= countLUTs*redundancy(i)
	//		mvGap(i) = redundancy(0)*repeatBase[0]*...*repeatBase[i-1] <= amplify(i)/countLUTs
	//      Note that the LUT generation needs to be modified
	// 	the noise bound is
	// 		bound(i) = Ceil(GaussianK * Sqrt(overflowVar + amplify(i)^2 * inputVar) + 1/2), for Gaussian input noise
	//				 = overflowBound+Ceil(amplify(i)/2*2^{-capacityBitsMeta})       , for bounded input noise
	// SampleExtract is correct when redundancy(i) >= 2*bound(i)+1,
	// 	whose necessary but insufficient condition is
	//		For Gaussian input noise:
	// 			redundancy(i) >= 2*Ceil(GaussianK*Sqrt(overflowVar + countLUTs^2*redundancy(i)^2 * inputVar) + 1/2) + 1,
	//     		we require countLUTs*2^-capBitsMeta < 1 for the corresponding function to be U-shaped
	//			also, the inequality is violated for redundancy(i)=0, meaning we need to take the right intersection point
	//		For bounded input noise:
	//			redundancy(i) >= (2*overflowBound+1)/(1 - countLUTs*2^{-capacityBitsMeta})
	//
	//  let truncBound(i) = bound(i)+floor(redundancy(i)/2) as defined previously, the truncation range is asymmetric:
	// 		[-truncBound(i),
	// 			truncBound(i)+(countLUTs-1)*mvGap(i)]
	// repeatBase[i] * (2*truncBound(i) + 1 + extendedCoeffsCount[i] + (countLUTs-1)*mvGap(i)) <= N
	solveMinRedundancy := func(_overflowVar float64, _inputVar float64, _gaussianK float64, _countLUTs int, _extRedundancy int) int {
		_countLUTsfloat := float64(_countLUTs)
		_extRedundancyfloat := float64(_extRedundancy)
		// a(redundancy+b)^2 >= c
		_a := 1 - 4*_gaussianK*_gaussianK*_countLUTsfloat*_countLUTsfloat*_inputVar
		_b := -_extRedundancyfloat / _a
		_c := 4*_gaussianK*_gaussianK*_overflowVar - _extRedundancyfloat*_extRedundancyfloat + _extRedundancyfloat*_extRedundancyfloat/_a
		_r := math.Ceil(-_b + math.Sqrt(_c/_a))
		if _r > 2048 {
			return 2048
		}
		for _r > 2*gaussianBound(_overflowVar+_r*_r*_countLUTsfloat*_countLUTsfloat*_inputVar, _gaussianK)+_extRedundancyfloat && _r > 1 {
			_r -= 1
		}
		for _r < 2*gaussianBound(_overflowVar+_r*_r*_countLUTsfloat*_countLUTsfloat*_inputVar, _gaussianK)+_extRedundancyfloat {
			_r += 1
		}
		return max(int(_r), 0)
	}

	N := params.polyDegree
	countLUTs := params.countLUTs
	requiredExtractionRedundancy := max(1, params.targetRedundancyInExtraction)
	// 2N/(full torus p)/countLUTs
	initRedundancy := float64(N/countLUTs) / float64(params.messageModulus)
	if params.fullTorus {
		initRedundancy *= 2
	}
	if params.fullDomain { // N/(full torus p)/countLUTs in FDFB
		initRedundancy /= 2
	}
	if initRedundancy < 1 {
		return params, fmt.Errorf("insufficient initial redundancy")
	}
	initAmplify := initRedundancy * float64(countLUTs) // 2N/(full torus p), or N/(full torus p) in FDFB
	debugf("Overflow bound is %f, initial redundancy is %f\n", overflowBound, initRedundancy)
	params.extendedCoeffsCount = make([]int, 0)
	params.repeatBase = make([]int, 0)
	params.truncationBound = make([]int, 0)
	params.redundancy = make([]int, 0)

	// core code for truncRepeat paramterization
	if float64(countLUTs)*math.Pow(2, -config.CapacityBitsMeta) >= 1 ||
		2*int(math.Ceil(initAmplify*math.Pow(2, -config.CapacityBitsMeta-1)))+1 > N {
		return params, fmt.Errorf("capacityBitsMeta too small")
	}
	requiredredundancyFinal := max(solveMinRedundancy(overflowVar, inputVar, GaussianK, countLUTs, requiredExtractionRedundancy),
		int(2*gaussianBound(overflowVar+initAmplify*initAmplify*inputVar, GaussianK)+float64(requiredExtractionRedundancy)))
	if !gaussianInput {
		requiredredundancyFinal = max(int(math.Ceil((2*overflowBound+float64(requiredExtractionRedundancy))/(1-float64(countLUTs)*math.Pow(2, -config.CapacityBitsMeta)))),
			+2*int(overflowBound+math.Ceil(initAmplify*math.Pow(2, -config.CapacityBitsMeta-1)))+requiredExtractionRedundancy)
	}
	if requiredredundancyFinal > N {
		return params, fmt.Errorf("required redundancy too large")
	}
	// recall:  repeatBase[i] * (2*truncBound(i) + 1 + extendedCoeffsCount[i] + (countLUTs-1)*mvGap(i)) <= N
	// 			truncBound(i) = bound(i)+redundancy(i)/2
	// 			bound(i) = Ceil(GaussianK * Sqrt(overflowVar + amplify(i)^2 * inputVar) + 1/2), for Gaussian input noise
	//					 = overflowBound+Ceil(amplify(i)/2*2^{-capacityBitsMeta})       , for bounded input noise
	//  		amplify(i) = 2N/p*repeatBase[0]*...*repeatBase[i-1]
	//			mvGap(i) = redundancy(0)*repeatBase[0]*...*repeatBase[i-1]
	// we want to decide the previous repeatBase, given the required redundancy in the next iter, thus
	// For Gaussian input noise:
	// repeatBase * (2 *
	// 					(
	// 					Ceil(GaussianK * Sqrt(overflowVar + amplify(i)^2 * inputVar) + 1/2) +
	// 					redundancy(i)/2
	// 					)
	// 					+ 1 + extendedCoeffsCount + mvGap * (countLUTs-1)
	// 				) <= N
	// For bounded input noise:
	// repeatBase * (2 *
	// 					(
	// 						overflowBound+
	// 						amplify/2*2^{-capacityBitsMeta} +
	// 						redundancy/2
	// 					)
	// 					+ 1 + extendedCoeffsCount + mvGap * (countLUTs-1)
	// 				) <= N
	// since amplify >= redundancy*countLUTs, mvGap >= redundancy
	// 	and redundancy >= nextRedundancy / repeatBase
	// 	the necessary but insufficient condition is
	// 	For bounded input noise:
	// 		repeatBase*(2*overflowBound+1+extendedCoeffsCount)
	// 			<= N-nextRedundancy*countLUTs*(1+2^{-capacityBitsMeta})
	//  For Gaussian input noise: another quadratic inequality of repeatBase (which we don't write down here...)
	//
	// NOTE: we use the necessary & insufficient condition to obtain upper bounds on repeatBases with extendedCoeffsCount=0
	//  then we search all the possiblities to find a good solution
	solveMaxRepeatBase := func(_overflowVar float64, _inputVar float64, _gaussianK float64, _countLUTs int, _N int, _nextRedundancy int) int {
		_countLUTsfloat := float64(_countLUTs)
		_Nfloat := float64(_N)
		_nextRedundancyfloat := float64(_nextRedundancy)
		// a(redundancy+b)^2 >= c
		_a := 4*_gaussianK*_gaussianK*_overflowVar - 1
		_b := (_Nfloat - _nextRedundancyfloat*_countLUTsfloat) / _a
		_c := math.Pow(_Nfloat-_nextRedundancyfloat*_countLUTsfloat, 2)*(1+1.0/_a) -
			4*_inputVar*math.Pow(_gaussianK*_nextRedundancyfloat*_countLUTsfloat, 2)
		if _c/_a < 0 {
			return 0
		}
		_base := math.Ceil(-_b + math.Sqrt(_c/_a))
		_curRedundancy := math.Ceil(_nextRedundancyfloat / _base)
		for _base*(2*gaussianBound(_overflowVar+math.Pow(_curRedundancy*_countLUTsfloat, 2)*_inputVar, _gaussianK)+
			2*math.Floor(_curRedundancy/2)+1+_curRedundancy*(_countLUTsfloat-1)) < _Nfloat {
			_base += 1
			_curRedundancy = math.Ceil(_nextRedundancyfloat / _base)
		}
		for _base*(2*gaussianBound(_overflowVar+math.Pow(_curRedundancy*_countLUTsfloat, 2)*_inputVar, _gaussianK)+
			2*math.Floor(_curRedundancy/2)+1+_curRedundancy*(_countLUTsfloat-1)) > _Nfloat && _base > 1 {
			_base -= 1
			_curRedundancy = math.Ceil(_nextRedundancyfloat / _base)
		}
		return int(_base)
	}

	// redundancyInExtraction is used in LWE-to-RLWE packing
	redundancyInExtraction := int(initRedundancy-2*gaussianBound(overflowVar+initAmplify*initAmplify*inputVar, GaussianK)-1) + requiredExtractionRedundancy - 1
	if !gaussianInput {
		redundancyInExtraction = int(initRedundancy-2*(overflowBound+math.Ceil(initAmplify*math.Pow(2, -config.CapacityBitsMeta-1)))-1) + requiredExtractionRedundancy - 1
	}
	// All current parameter-search targets require K >= 1; this path does not support K = 0.
	if redundancyInExtraction < 0 {
		curIter := 0
		// estimate the number of iters
		for requiredRedundancy := requiredredundancyFinal; ; {
			params.redundancy = append(params.redundancy, requiredRedundancy)
			if float64(requiredRedundancy) <= initRedundancy {
				params.itersCount = curIter
				break
			}
			// assume extendedCoeffsCount = 0 when searching
			base := solveMaxRepeatBase(overflowVar, inputVar, GaussianK, countLUTs, N, requiredRedundancy)
			if !gaussianInput {
				base = int(math.Floor((float64(N) - float64(requiredRedundancy)*float64(countLUTs)*(1+math.Pow(2, -config.CapacityBitsMeta))) /
					(2*overflowBound + 1)))
			}
			if base <= 1 {
				return params, fmt.Errorf("failed to realize Meta-FBS at iter %d", curIter)
			}
			requiredRedundancy = (requiredRedundancy + base - 1) / base
			params.repeatBase = append(params.repeatBase, base)
			curIter++
		}
		vec.ReverseInPlace(params.repeatBase) // len itersCount
		debugln("Initial suggested repeatBase:", params.repeatBase)

		// many sure the slices in params has the correct length
		func_reserve_params := func(itersCount int) {
			params.itersCount = itersCount
			trLen := itersCount
			if params.fullDomain {
				trLen += 1
			}
			if curLen := len(params.extendedCoeffsCount); curLen < trLen {
				params.extendedCoeffsCount = append(params.extendedCoeffsCount, make([]int, trLen-curLen)...)
			}
			if curLen := len(params.repeatBase); curLen < trLen {
				params.repeatBase = append(params.repeatBase, make([]int, trLen-curLen)...)
			}
			if curLen := len(params.truncationBound); curLen < trLen {
				params.truncationBound = append(params.truncationBound, make([]int, trLen-curLen)...)
			}
			if curLen := len(params.redundancy); curLen < trLen {
				params.redundancy = append(params.redundancy, make([]int, trLen-curLen)...)
			}
			if curLen := len(params.amplify); curLen < itersCount {
				params.amplify = append(params.amplify, make([]int, itersCount-curLen)...)
			}
			// last entry in mvGap required for sample extraction
			if curLen := len(params.mvGap); curLen < itersCount+1 {
				params.mvGap = append(params.mvGap, make([]int, itersCount+1-curLen)...)
			}
			params.extendedCoeffsCount = params.extendedCoeffsCount[:itersCount]
			params.repeatBase = params.repeatBase[:itersCount]
			params.truncationBound = params.truncationBound[:itersCount]
			params.redundancy = params.redundancy[:itersCount]
			params.amplify = params.amplify[:itersCount]
			params.mvGap = params.mvGap[:itersCount+1]
		} // end func_reserve_params
		// funcTrial return the estimated cost of the current choice of bases, and modifies the Meta-FBS members in params
		funcTrial := func(bases []int) float64 {
			// given the bases, we can have an accurate estimation of required redundancy (in reserve order)
			finalAmplify := int(initAmplify)
			for _, base := range bases {
				finalAmplify *= base
			}
			params.itersCount = len(bases)

			requiredRedundancy := 2*int(gaussianBound(overflowVar+float64(finalAmplify*finalAmplify)*inputVar, GaussianK)) + requiredExtractionRedundancy
			if !gaussianInput {
				requiredRedundancy = 2*int(math.Ceil(overflowBound+float64(finalAmplify)*math.Pow(2, -config.CapacityBitsMeta-1))) + requiredExtractionRedundancy
			}
			for i := params.itersCount - 1; i >= 0; i-- {
				base := bases[i]
				if base <= 1 {
					return math.Inf(1)
				}
				requiredRedundancy = (requiredRedundancy + base - 1) / base
				params.redundancy[i] = requiredRedundancy
				if i == 0 && requiredRedundancy > int(initRedundancy) {
					return math.Inf(1)
				}
			}
			// In ordinary order, check params
			amplify := int(initAmplify) // 2N/p
			mvGap := params.redundancy[0]

			cost := float64(params.CountBlindRotations() * 2 * N)
			for i := range params.itersCount {
				params.amplify[i] = amplify
				params.mvGap[i] = mvGap
				redundancy := params.redundancy[i]
				base := bases[i]

				bound := int(gaussianBound(overflowVar+float64(amplify*amplify)*inputVar, GaussianK))
				if !gaussianInput {
					bound = int(math.Ceil(overflowBound + float64(amplify)*math.Pow(2, -1-config.CapacityBitsMeta)))
				}
				truncBound := bound + redundancy/2
				e := N/base - 2*truncBound - 1 - int(mvGap)*(countLUTs-1)
				if e < 0 {
					return math.Inf(1)
				}
				cost += float64((N + e) / (e + 1))
				params.extendedCoeffsCount[i] = e
				params.truncationBound[i] = truncBound
				amplify *= base
				mvGap *= base
			}
			bound := int(gaussianBound(overflowVar+float64(amplify*amplify)*inputVar, GaussianK))
			if !gaussianInput {
				bound = int(math.Ceil(overflowBound + float64(amplify)*math.Pow(2, -1-config.CapacityBitsMeta)))
			}
			if params.redundancy[params.itersCount-1]*bases[params.itersCount-1] < 2*bound+requiredExtractionRedundancy {
				return math.Inf(1)
			}
			params.mvGap[params.itersCount] = mvGap

			if params.fullDomain {
				params.redundancy = params.redundancy[:params.itersCount+1]
				params.repeatBase = params.repeatBase[:params.itersCount+1]
				params.truncationBound = params.truncationBound[:params.itersCount+1]
				params.extendedCoeffsCount = params.extendedCoeffsCount[:params.itersCount+1]
				// information about LWE-to-RLWE packing
				// bound < overflowBound + 2N/(full torus p)*|input err|, initAmplify = N/(full torus p)
				redundancyRequiredForCancelSign := 2*int(gaussianBound(
					overflowVar+math.Pow(2*initAmplify, 2)*inputVar/capacityFactor, GaussianK)) + 1
				packingDistance := N / params.countCancelSignLUTs
				if !gaussianInput {
					redundancyRequiredForCancelSign =
						int(2 * (overflowBound + math.Ceil(2*initAmplify*math.Pow(2, -1-config.CapacityBitsMeta)) + 1))
				}
				var packingBase int
				var packingExtendedCoeffsCount int

				afterBtsRedundancy := params.redundancy[params.itersCount-1]*bases[params.itersCount-1] - 2*bound
				packingBase = (redundancyRequiredForCancelSign + afterBtsRedundancy - 1) / afterBtsRedundancy
				afterBtsRedundancy = (redundancyRequiredForCancelSign + packingBase - 1) / packingBase
				params.redundancy[params.itersCount] = afterBtsRedundancy

				params.truncationBound[params.itersCount] = afterBtsRedundancy / 2
				packingExtendedCoeffsCount = packingDistance/packingBase - 2*params.truncationBound[params.itersCount] - 1
				if packingExtendedCoeffsCount < 0 {
					return math.Inf(1)
				}
				params.repeatBase[params.itersCount] = packingBase
				params.extendedCoeffsCount[params.itersCount] = packingExtendedCoeffsCount

				cost += float64(countLUTs-1) * float64((N+packingExtendedCoeffsCount)/(packingExtendedCoeffsCount+1))
			}

			return cost
		} // end funcTrial

		maxIters := curIter + 1
		bestCost := math.Inf(1)
		bestBase := make([]int, maxIters)
		tmpBase := make([]int, maxIters)

		// recursively try all tmpBase with tmpBase[i] <= params.repeatBases[i]
		// start from the last base
		var funcRecur func(int)
		funcRecur = func(idx int) {
			for i := 2; i <= params.repeatBase[idx]; i++ {
				tmpBase[idx] = i
				if idx == 0 {
					cost := funcTrial(tmpBase)
					if cost < bestCost {
						bestCost = cost
						copy(bestBase, tmpBase)
					}
				} else {
					funcRecur(idx - 1)
				}
			}
		} // end funcRecur
		// a more adaptive searching
		// start from the last base but with inverse indexing
		var funcRecur2 func(int, int)
		funcRecur2 = func(idx int, requiredRedundancy int) {
			if idx == maxIters && requiredRedundancy > int(initRedundancy) {
				return
			}
			if float64(requiredRedundancy) <= initRedundancy {
				curBases := vec.Reverse(tmpBase[:idx])
				cost := funcTrial(curBases)
				if cost < bestCost {
					bestCost = cost
					bestBase = bestBase[:len(curBases)]
					copy(bestBase, curBases)
				}
				return
			}
			maxBase := solveMaxRepeatBase(overflowVar, inputVar, GaussianK, countLUTs, N, requiredRedundancy)
			if !gaussianInput {
				maxBase = int(math.Floor((float64(N) - float64(requiredRedundancy)*float64(countLUTs)*(1+math.Pow(2, -config.CapacityBitsMeta))) /
					(2*overflowBound + 1)))
			}
			for base := 2; base <= maxBase; base++ {
				requiredRedundancyNextIter := (requiredRedundancy + base - 1) / base
				tmpBase[idx] = base
				funcRecur2(idx+1, requiredRedundancyNextIter)
			}
		}

		oldRecur := false
		if oldRecur {
			func_reserve_params(curIter)
			tmpBase = make([]int, curIter)
			bestBase = make([]int, curIter)
			funcRecur(params.itersCount - 1)
		} else {
			func_reserve_params(maxIters)
			funcRecur2(0, requiredredundancyFinal)
		}
		if bestCost == math.Inf(1) {
			return params, fmt.Errorf("failed to find META-FBS parameters")
		}
		if len(bestBase) != curIter {
			fmt.Println("\033[31mWarning: more iters than first estimated\033[0m")
		}
		func_reserve_params(len(bestBase))
		copy(params.repeatBase, bestBase)
		funcTrial(bestBase)
		// redundancyInExtraction = params.redundancy[params.itersCount] -
		// (2*params.truncationBound[params.itersCount] + 1) + 1
	}

	// if params.fullDomain {
	// 	// information about LWE-to-RLWE packing
	// 	// bound < overflowBound + 2N/(full torus p)*|input err|, initAmplify = N/(full torus p)
	// 	redundancyRequiredForCancelSign := 2*int(math.Ceil(GaussianK*math.Sqrt(
	// 		overflowVar+math.Pow(2*initAmplify, 2)*inputVar/capacityFactor))) + 1
	// 	packingDistance := N / params.countCancelSignLUTs
	// 	if !gaussianInput {
	// 		redundancyRequiredForCancelSign =
	// 			int(2 * (overflowBound + math.Ceil(2*initAmplify*math.Pow(2, -1-config.CapacityBitsMeta)) + 1))
	// 	}
	// 	var packingBase int
	// 	var packingExtendedCoeffsCount int

	// 	afterBtsRedundancy := params.redundancy[params.itersCount]
	// 	packingBase = (redundancyRequiredForCancelSign + afterBtsRedundancy - 1) / afterBtsRedundancy
	// 	afterBtsRedundancy = (redundancyRequiredForCancelSign + packingBase - 1) / packingBase
	// 	params.redundancy[params.itersCount] = afterBtsRedundancy

	// 	params.truncationBound[params.itersCount] = afterBtsRedundancy / 2
	// 	packingExtendedCoeffsCount = packingDistance/packingBase - 2*params.truncationBound[params.itersCount] - 1
	// 	if packingExtendedCoeffsCount < 0 {
	// 		return params, fmt.Errorf("failed to truncRepeat before CancelSign")
	// 	}
	// 	params.repeatBase = append(params.repeatBase, packingBase)
	// 	params.redundancy = append(params.redundancy, redundancyRequiredForCancelSign)
	// 	params.extendedCoeffsCount = append(params.extendedCoeffsCount, packingExtendedCoeffsCount)
	// }

	// decide gadget parameters for Br, Ks, and Tr
	countBlindRotations := params.CountBlindRotations()
	countTruncRepeats := params.CountTruncRepeats()
	params.truncatedRepetitionParameters = make([]GadgetParameters[T], countTruncRepeats)
	maxVar := math.Pow(float64(params.scale)/2/GaussianK, 2) / math.Pow(2, 2*config.CapacityBitsMeta)
	maxBrVar := maxVar / capacityFactor / float64(countBlindRotations)
	maxTrVar := maxVar / capacityFactor // total variance for all truncRepeats
	// helper function that finds the Btr values minimizing output error
	funcBestBtr := func() float64 {
		Btrs := params.MinimizeAllTruncRepeatVarianceBtr()
		for i := range Btrs {
			Btr := NextPowerOfTwo(uint(Btrs[i]))
			funcUpdateBase(&params.truncatedRepetitionParameters[i], T(Btr))
			var1 := math.Pow(params.EstimateAllTruncRepeatStdDev(), 2)
			funcUpdateBase(&params.truncatedRepetitionParameters[i], T(Btr)>>1)
			var2 := math.Pow(params.EstimateAllTruncRepeatStdDev(), 2)
			if var1 < var2 {
				funcUpdateBase(&params.truncatedRepetitionParameters[i], T(Btr))
			}
		}
		return math.Pow(params.EstimateAllTruncRepeatStdDev(), 2)
	}
	// find the smallest Lbr satisfying BrVar < maxBrVar
	for Lbr := 1; Lbr <= config.MaxGadgetLength; Lbr++ {
		params.blindRotateParameters.level = Lbr
		curVar := funcBestBbr()
		if curVar < maxBrVar {
			break
		}
		if Lbr == config.MaxGadgetLength {
			return params, fmt.Errorf("failed to find Lbr")
		}
	}
	// find the smallest Lks satisfying KsVar < maxVar
	for Lks := 1; Lks <= config.MaxGadgetLength; Lks++ {
		params.keySwitchParameters.level = Lks
		curVar := funcBestBks()
		if curVar < maxVar {
			break
		}
		if Lks == config.MaxGadgetLength {
			return params, fmt.Errorf("failed to find Lks")
		}
	}
	// find the smallest Ltr satisfying TrVar < maxTrVar
	for Ltr := 1; Ltr <= config.MaxGadgetLength; Ltr++ {
		for i := range countTruncRepeats {
			params.truncatedRepetitionParameters[i].level = Ltr
		}
		curVar := funcBestBtr()
		if curVar < maxTrVar {
			break
		}
		if Ltr == config.MaxGadgetLength {
			return params, fmt.Errorf("failed to find Ltr")
		}
	}
	totalVariance := func(varBr float64, varTr float64, varKs float64) float64 {
		return capacityFactor*(varBr*float64(countBlindRotations)+
			varTr) + varKs
	}
	// check the variance
	for { // loop Bbr
		ksGadget := params.keySwitchParameters
		var trGadgetList []GadgetParameters[T] = make([]GadgetParameters[T], countTruncRepeats)
		copy(trGadgetList, params.truncatedRepetitionParameters)
		varBr := funcBestBbr()
		found := false
		for { // loop Btr
			varTr := funcBestBtr()
			for params.keySwitchParameters.level <= config.MaxGadgetLength { // loop Bks
				if totalVariance(varBr, varTr, funcBestBks()) < maxVar {
					found = true
					break
				}
				params.keySwitchParameters.level++
			}
			if found {
				break
			}
			params.keySwitchParameters = ksGadget
			breakFlag := false
			for i := range params.truncatedRepetitionParameters {
				if params.truncatedRepetitionParameters[i].level < config.MaxGadgetLength {
					params.truncatedRepetitionParameters[i].level++
				} else {
					breakFlag = true
					break
				}
			}
			if breakFlag {
				break
			}
		}
		if found {
			break
		}
		params.keySwitchParameters = ksGadget
		copy(params.truncatedRepetitionParameters, trGadgetList)
		params.blindRotateParameters.level++
		if params.blindRotateParameters.level > config.MaxGadgetLength {
			return params, fmt.Errorf("failed to find gadget parameters in Meta-FBS")
		}
	}

	return params, nil
}

func costFunc[T TorusInt](p Parameters[T]) float64 {
	cost := 0.0
	brCount := float64(p.CountBlindRotations())
	N := float64(p.glweDimension)
	// blind rotation
	cost += brCount * float64(p.blindRotateParameters.level+1) * N * 2
	// truncRepeat
	for i := range p.truncatedRepetitionParameters {
		Ltr := p.truncatedRepetitionParameters[i].level
		e := p.extendedCoeffsCount[i]
		trkCount := (p.polyDegree + e) / (e + 1)
		callCount := 1
		if i == p.itersCount {
			callCount = p.countLUTs - 1
		}
		cost += float64((Ltr + 1) * trkCount * callCount)
	}
	// key switch
	cost += float64(p.keySwitchParameters.level)
	return cost
}

func SweepParameterAuto[T TorusInt](paramsLit ParametersLiteral[T], config *SweepConfig) (params Parameters[T]) {
	minCost := math.Inf(1)
	var bestCapBitsMeta float64
	var bestRedundancy int
	var tmpParams Parameters[T]
	var err error
	for capBitsMeta := config.CapacityBitsMetaBegin; capBitsMeta <= config.CapacityBitsMetaEnd; capBitsMeta += config.CapacityBitsMetaStep {
		for requiredExtractionRedundancy := config.RequiredExtractionRedundancyBegin; requiredExtractionRedundancy <= config.RequiredExtractionRedundancyEnd; requiredExtractionRedundancy++ {
			config.CapacityBitsMeta = capBitsMeta
			paramsLit.TargetRedundancyInExtraction = requiredExtractionRedundancy
			tmpParams, err = SweepParameter(paramsLit, *config)
			if err != nil {
				fmt.Printf("Error for capBitsMeta = %.3f, extraction redundancy = %d: %s\n", capBitsMeta, requiredExtractionRedundancy, err)
				continue
			}
			curCost := costFunc(tmpParams)
			if curCost < minCost {
				minCost = curCost
				params = tmpParams
				bestCapBitsMeta = capBitsMeta
				bestRedundancy = requiredExtractionRedundancy
				params.TruncRepeatParameters = tmpParams.TruncRepeatParameters.Copy()
			}
		}
	}
	if math.IsInf(minCost, 1) {
		panic("Failed to find Meta-FBS parameters")
	}
	fmt.Printf("Best capBitsMeta = %.3f, extraction redundancy = %d\n", bestCapBitsMeta, bestRedundancy)
	config.CapacityBitsMeta = bestCapBitsMeta
	params.targetRedundancyInExtraction = bestRedundancy
	return params
}

// estimateCompressedEvaluationKeyBodySize returns the evaluation-key size when all
// encryption masks are generated from a shared seed, leaving only ciphertext bodies.
func (p Parameters[T]) estimateCompressedEvaluationKeyBodySize() int {
	torusBytes := num.ByteSizeT[T]()
	brSize := p.lweDimension * (p.glweRank + 1) * p.blindRotateParameters.level * p.polyDegree * torusBytes
	ksSize := max(p.glweDimension-p.lweDimension, 0) * p.keySwitchParameters.level * torusBytes

	trSize := 0
	seenTRKeys := make(map[[4]uint64]struct{})
	for i := range p.CountTruncRepeats() {
		keyID := [4]uint64{
			uint64(p.repeatBase[i]),
			uint64(p.extendedCoeffsCount[i]),
			uint64(p.truncatedRepetitionParameters[i].Base()),
			uint64(p.truncatedRepetitionParameters[i].Level()),
		}
		if _, ok := seenTRKeys[keyID]; ok {
			continue
		}
		seenTRKeys[keyID] = struct{}{}
		trkCount := (p.polyDegree + p.extendedCoeffsCount[i]) / (p.extendedCoeffsCount[i] + 1)
		trSize += trkCount * p.truncatedRepetitionParameters[i].level * p.polyDegree * torusBytes
	}
	return brSize + ksSize + trSize
}

func PrintParamsNoiseLevel[T TorusInt](p Parameters[T], config SweepConfig) {
	stddevMS := p.EstimateModSwitchStdDev()
	stddevBR := p.EstimateBlindRotateStdDev()
	stddevKS := p.EstimateKeySwitchForBootstrapStdDev()
	stddevTr := p.EstimateAllTruncRepeatStdDev()

	varMS := stddevMS * stddevMS
	varBR := stddevBR * stddevBR
	varKS := stddevKS * stddevKS
	varTr := stddevTr * stddevTr

	k := GaussianBoundForFailureProb(p.WorstCaseLogFailureProb())
	capFactorPow2 := math.Pow(2, 2*config.CapacityBits)
	capFactorMetaPow2 := math.Pow(2, 2*config.CapacityBitsMeta)
	thres := float64(p.Scale()) / 2
	maxVar := math.Pow(thres/k, 2)

	if !p.MetaFBS() {
		fmt.Printf("BR capacity: 2^%f\n", math.Log2(thres/(k*stddevBR)))
		fmt.Printf("KS capacity: 2^%f\n", math.Log2(thres/(k*stddevKS)))
		fmt.Printf("MS capacity: 2^%f\n", math.Log2(thres/(k*stddevMS)))
		fmt.Printf("Homomorphic capacity: 2^%f\n", math.Log2(math.Sqrt(
			(maxVar-varMS-varKS)/varBR)))
		fmt.Printf("Final capacity: 2^%f\n", math.Log2(math.Sqrt(
			maxVar/(varKS+varMS+varBR*capFactorPow2))))
	} else {
		fmt.Printf("Target capacities: c_Hom >= %.6f bits, c_meta >= %.6f bits\n",
			config.CapacityBits, config.CapacityBitsMeta)
		fmt.Printf("Gadget parameters: B_br=%d, l_br=%d, B_ks=%d, l_ks=%d\n",
			p.blindRotateParameters.Base(), p.blindRotateParameters.Level(),
			p.keySwitchParameters.Base(), p.keySwitchParameters.Level())
		fmt.Printf("Target extraction redundancy: %d\n", p.TargetRedundancyInExtraction())
		eventCount := p.itersCount + 1
		if p.fullDomain {
			eventCount++
		}
		fmt.Printf("Failure probability: per event 2^%d, union bound (%d events) <= 2^%f\n",
			p.worstCaseLogFailureProb, eventCount,
			float64(p.worstCaseLogFailureProb)+math.Log2(float64(eventCount)))

		if p.itersCount > 0 {
			gaussianBound := func(variance float64) int {
				return int(math.Ceil(k*math.Sqrt(variance) + 0.5))
			}
			overflowVar := math.Pow(p.EstimateOverflowStdDev(), 2)
			inputVar := math.Pow(math.Pow(2, -config.CapacityBitsMeta-1)/k, 2)
			overflowBound := gaussianBound(overflowVar)

			fmt.Printf("Meta-PBS iterations: K = %d\n", p.itersCount)
			fmt.Println("Iteration parameters:")
			var finalRedundancy int
			// Only the first K bases are Meta-PBS iterations; any later base is for FDFB packing.
			for i := 0; i < p.itersCount; i++ {
				redundancy := p.redundancy[i]
				base := p.repeatBase[i]
				delta := p.truncationBound[i] - redundancy/2
				trkParams := p.truncatedRepetitionParameters[i]
				if p.countLUTs > 1 {
					fmt.Printf("  i=%d: beta_%d=%d, r_%d=%d, delta_%d=%d, T_%d=%d, epsilon_%d=%d, D_%d=%d, B_tr,%d=%d, l_tr,%d=%d\n",
						i, i, base, i, redundancy, i, delta, i, p.truncationBound[i], i, p.extendedCoeffsCount[i],
						i, p.mvGap[i], i, trkParams.Base(), i, trkParams.Level())
				} else {
					fmt.Printf("  i=%d: beta_%d=%d, r_%d=%d, delta_%d=%d, T_%d=%d, epsilon_%d=%d, B_tr,%d=%d, l_tr,%d=%d\n",
						i, i, base, i, redundancy, i, delta, i, p.truncationBound[i], i, p.extendedCoeffsCount[i],
						i, trkParams.Base(), i, trkParams.Level())
				}

				maxNextRedundancy := base * redundancy
				nextRedundancy := maxNextRedundancy
				if i+1 < p.itersCount {
					nextRedundancy = p.redundancy[i+1]
				}
				if nextRedundancy == maxNextRedundancy {
					fmt.Printf("    r_%d = beta_%d * r_%d = %d * %d = %d\n",
						i+1, i, i, base, redundancy, nextRedundancy)
				} else {
					fmt.Printf("    r_%d = %d <= beta_%d * r_%d = %d * %d = %d\n",
						i+1, nextRedundancy, i, i, base, redundancy, maxNextRedundancy)
				}
				finalRedundancy = nextRedundancy
			}

			finalAmplify := p.amplify[p.itersCount-1] * p.repeatBase[p.itersCount-1]
			var finalDelta int
			if p.inputNoiseIsGaussian {
				finalDelta = gaussianBound(overflowVar + float64(finalAmplify*finalAmplify)*inputVar)
			} else {
				finalDelta = overflowBound + int(math.Ceil(float64(finalAmplify)*math.Pow(2, -config.CapacityBitsMeta-1)))
			}
			fmt.Printf("Final Meta-PBS state: r_%d=%d, delta_%d=%d",
				p.itersCount, finalRedundancy, p.itersCount, finalDelta)
			if p.countLUTs > 1 {
				fmt.Printf(", D_%d=%d", p.itersCount, p.mvGap[p.itersCount])
			}
			fmt.Println()

			availableRedundancy := finalRedundancy - 2*finalDelta
			fmt.Printf("Available extraction redundancy: r_%d - 2*delta_%d = %d\n",
				p.itersCount, p.itersCount, availableRedundancy)

			if p.fullDomain {
				cancelSignIdx := p.itersCount
				cancelSignRedundancy := p.redundancy[cancelSignIdx]
				cancelSignBase := p.repeatBase[cancelSignIdx]
				cancelSignDelta := 0
				if p.inputNoiseIsGaussian {
					cancelSignDelta = gaussianBound(overflowVar +
						math.Pow(float64(2*p.amplify[0]), 2)*inputVar/capFactorPow2)
				} else {
					cancelSignDelta = overflowBound +
						int(math.Ceil(float64(2*p.amplify[0])*math.Pow(2, -config.CapacityBitsMeta-1))) + 1
				}
				cancelSignTRParams := p.truncatedRepetitionParameters[cancelSignIdx]
				nu := bits.Len(uint(p.countLUTs)) - 1
				fmt.Printf("Meta-WoP-PBS parameters: nu=%d, tau=%d\n", nu, p.countCancelSignLUTs)
				logGadgetBases := make([]int, p.countLUTs-1)
				gadgetCapacity := p.CapacityForGadgetMultAssign(p.countLUTs-1, logGadgetBases)
				linearCombinationCount := math.Exp2(2 * (config.CapacityBits - gadgetCapacity))
				fmt.Printf("Configured linear-combination count: L=%.0f\n", linearCombinationCount)
				fmt.Printf("CancelSign: beta_CS=%d, r_ext=%d, delta_CS=%d, epsilon_CS=%d, B_tr,CS=%d, l_tr,CS=%d\n",
					cancelSignBase, cancelSignRedundancy, cancelSignDelta, p.extendedCoeffsCount[cancelSignIdx],
					cancelSignTRParams.Base(), cancelSignTRParams.Level())
				fmt.Printf("CancelSign output redundancy lower bound: %d * %d - 2 * %d = %d\n",
					cancelSignRedundancy, cancelSignBase, cancelSignDelta,
					cancelSignRedundancy*cancelSignBase-2*cancelSignDelta)
			}
		}
		if !p.isDummyPublicFunctionalKeySwitch {
			fmt.Printf("Estimated compressed evaluation key size (body only): %.2f MiB\n",
				float64(p.estimateCompressedEvaluationKeyBodySize())/(1<<20))
		}
		fmt.Printf("All BR capacity: 2^%f\n", math.Log2(thres/(k*stddevBR*math.Sqrt(float64(p.CountBlindRotations())))))
		fmt.Printf("Randomized blind rotation: %t\n", p.RandomizedBlindRotate)
		fmt.Printf("KS capacity: 2^%f\n", math.Log2(thres/(k*stddevKS)))
		fmt.Printf("All TR capacity: 2^%f\n", math.Log2(thres/(k*stddevTr)))
		if p.FullDomain() {
			maxBatchSize := p.maxCancelSignBatchSize()
			lastBatchSize := (p.countLUTs - 1) % maxBatchSize
			if lastBatchSize == 0 {
				lastBatchSize = maxBatchSize
			}
			lastBatchStdDev := p.estimateAllTruncRepeatStdDev(lastBatchSize)
			fmt.Printf("Last-batch all TR stddev (tau_j=%d): 2^%f\n", lastBatchSize, math.Log2(lastBatchStdDev))
		}
		fmt.Printf("Fresh MetaPBS stddev: 2^%f\n", math.Log2(math.Sqrt(float64(p.CountBlindRotations())*varBR+varTr)))
		fmt.Printf("Homomorphic capacity: 2^%f\n", math.Log2(math.Sqrt(
			(maxVar/capFactorMetaPow2-varKS)/(float64(p.CountBlindRotations())*varBR+varTr))))
		fmt.Printf("Final capacity (including capacity for Meta-FBS): 2^%f\n", math.Log2(math.Sqrt(
			maxVar/(varBR*float64(p.CountBlindRotations())*capFactorPow2+varTr*capFactorPow2+varKS))))
	}
}
