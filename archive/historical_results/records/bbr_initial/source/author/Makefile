VENV ?= .venv_artifact_tches
BIN := $(VENV)/bin
PYTHON := $(BIN)/python
PIP := $(PYTHON) -m pip
MATURIN := $(BIN)/maturin

DECOMPOSER_DIR := $(abspath decomposer)
REQ := $(DECOMPOSER_DIR)/requirements.txt
GAUSS_RUST_MANIFEST := $(DECOMPOSER_DIR)/src/gauss_elimination_rs/Cargo.toml
STAMP := $(VENV)/.installed

CJP_DIR := $(abspath bench/bench_cjp/cjp)
HLUT_DIR := $(abspath bench/HLUT-rs)
TREE_PBS_DIR := $(abspath bench/bench_tree_pbs)
WOPPBS_DIR := $(abspath bench/bench_woppbs)
OUTPUT_DIR_WOPPBS := $(abspath data/generated)
DATAFOLDER := $(abspath data)

FIGURE_DIR := $(abspath figures)

BENCH ?= all
PERROR ?= 40
GAMMA ?= 1.05
DECOMPOSITIONS_DIR = $(abspath decompositions/regenerated/)


.PHONY: install reinstall clean bench \
        bench-hlut-full bench-hlut-partial bench-tbm bench-woppbs plots



install: $(STAMP)

check_mode:
ifeq ($(filter $(MODE),paper regenerated),)
	$(error MODE must be either "paper" or "regenerated")
endif

$(PYTHON):
	@echo "Creating virtualenv in $(VENV)"
	python3 -m venv $(VENV)

$(STAMP): $(PYTHON) $(REQ)
	@echo "Installing Python dependencies"
	$(PIP) install -r $(REQ)
	@echo "Installing decomposer package"
	$(PIP) install -e $(DECOMPOSER_DIR)
	@echo "Building Rust extension with maturin"
	VIRTUAL_ENV=$(VENV) PATH="$(BIN):$(PATH)" $(MATURIN) develop --release -m $(GAUSS_RUST_MANIFEST)
	@touch $(STAMP)

reinstall: clean install

clean:
	@echo "Removing virtualenv"
	rm -rf $(VENV)
	@echo "Cleaning compiled Rust projects"
	cargo clean --manifest-path $(CJP_DIR)/Cargo.toml
	cargo clean --manifest-path $(CJP_DIR)/../tfhe-rs/Cargo.toml
	cargo clean --manifest-path $(HLUT_DIR)/Cargo.toml
	cargo clean --manifest-path $(TREE_PBS_DIR)/Cargo.toml
	cargo clean --manifest-path $(WOPPBS_DIR)/Cargo.toml
	cargo clean --manifest-path $(WOPPBS_DIR)/../tfhe-rs-odd/Cargo.toml
	cargo clean --manifest-path $(GAUSS_RUST_MANIFEST)
	rm -f $(DECOMPOSER_DIR)/src/decomposer/*.so


bench:
	@echo "Requested benchmark: $(BENCH)"
	@if [ "$(BENCH)" = "all" ]; then \
		$(MAKE) bench-cjp; \
		$(MAKE) bench-tbm; \
		$(MAKE) bench-hlut-full PERROR=40 MODE=paper; \
		$(MAKE) bench-hlut-partial PERROR=4 MODE=paper; \
		$(MAKE) bench-woppbs; \
	elif [ "$(BENCH)" = "hlut-full" ]; then \
		$(MAKE) bench-hlut-full PERROR=$(PERROR) MODE=$(MODE); \
	elif [ "$(BENCH)" = "hlut-partial" ]; then \
		$(MAKE) bench-hlut-partial PERROR=$(PERROR) MODE=$(MODE); \
	elif [ "$(BENCH)" = "tbm" ]; then \
		$(MAKE) bench-tbm; \
	elif [ "$(BENCH)" = "woppbs" ]; then \
		$(MAKE) bench-woppbs; \
	elif [ "$(BENCH)" = "cjp" ]; then \
		$(MAKE) bench-cjp; \
	else \
		echo "Unknown BENCH=$(BENCH)"; \
		echo "Valid values: all hlut-full hlut-partial tbm woppbs"; \
		exit 1; \
	fi

decompositions: $(STAMP)
	$(BIN)/run-search-decomposition --output $(DECOMPOSITIONS_DIR) --gamma $(GAMMA)


bench-hlut-full:
	@echo "Running benchmark for our technique. Only the m-to-m S-box sizes, for a perror of $(PERROR)"
	cargo run --release --locked --manifest-path $(HLUT_DIR)/Cargo.toml full --perror $(PERROR) --mode $(MODE)

bench-hlut-partial:
	@echo "Running benchmark for our technique. Regenerates data of Figure 9, for a perror of $(PERROR)"
	cargo run --release --manifest-path $(HLUT_DIR)/Cargo.toml partial --perror $(PERROR) --mode $(MODE)

bench-tbm:
	@echo "Running benchmark for TBM"
	cargo run --release --manifest-path $(TREE_PBS_DIR)/Cargo.toml

bench-woppbs: $(STAMP)
	@echo "Running WOPPBS benchmark"
	cargo bench --manifest-path $(WOPPBS_DIR)/Cargo.toml --bench woppbs-hlut-bench
	@echo "Processing results"
	$(PYTHON) $(DECOMPOSER_DIR)/src/decomposer/plots/format_woppbs_data.py


bench-cjp: $(STAMP)
	@echo "Running Simple PBS (CJP) benchmark"
	cargo run --release --manifest-path $(CJP_DIR)/Cargo.toml


experiments: $(STAMP)
	$(MAKE) experiments-ranks-distribution
	$(MAKE) experiments-correlation-margin-ranks
	$(MAKE) experiments-count-pbs
	$(MAKE) experiments-encodings
	$(MAKE) experiments-shapes

experiments-ranks-distribution: $(STAMP)
	@echo "Experiment on the distribution of the ranks of the matrices (Figure 5)"
	$(BIN)/experiments-ranks-distribution --output $(DATAFOLDER)/regenerated/ranks/

experiments-correlation-margin-ranks: $(STAMP)
	@echo "Experiemnt on the correlation between the margin on the dimension bound and the ranks of the matrices (Figure 6)"
	$(BIN)/experiments-correlation-margin-ranks --output $(DATAFOLDER)/regenerated/correlation_margin_ranks/

experiments-shapes: $(STAMP)
	@echo "Experiment on the shapes of the decompositions with respect to the gamma parameter (Table 1)"
	$(BIN)/generate_tables_size_data --output $(DATAFOLDER)/regenerated/shapes/

experiments-count-pbs: $(STAMP)
	@echo "Experiment on the count of PBS per decomposition (Table 2)"
	$(BIN)/generate_tables_count_pbs_data --output $(DATAFOLDER)/regenerated/shapes/

experiments-encodings: $(STAMP)
	@echo "Experiment on the acceleration of the seach when using encoding techniques (Table 3)"
	$(BIN)/experiments-encodings --output $(DATAFOLDER)/regenerated/encodings/  > /dev/null 2>&1



plots: $(STAMP)
ifeq ($(MODE),paper)
	@echo "Generating the plots from the data of the paper"
else ifeq ($(MODE),regenerated)
	@echo "Generating the plots from the regenerated data"
endif
	$(BIN)/plot-comparison-soa --mode $(MODE) --output $(FIGURE_DIR)/$(MODE)
	$(BIN)/format_tables_size --input $(DATAFOLDER)/$(MODE)/shapes/ --output $(FIGURE_DIR)/$(MODE)
	$(BIN)/plot-comparison-soa-intro --mode $(MODE) --output $(FIGURE_DIR)/$(MODE)
	$(BIN)/format-tables-benches --input $(DATAFOLDER)/$(MODE) --output $(FIGURE_DIR)/$(MODE) --perror 40
	$(BIN)/format-tables-benches --input $(DATAFOLDER)/$(MODE) --output $(FIGURE_DIR)/$(MODE) --perror 128
	$(BIN)/plot-ranks-distributions --input $(DATAFOLDER)/$(MODE)/ranks --output $(FIGURE_DIR)/$(MODE)
	$(BIN)/plot-correlation-margin-ranks --input $(DATAFOLDER)/$(MODE)/correlation_margin_ranks --output $(FIGURE_DIR)/$(MODE)
	$(BIN)/plot-encodings --input $(DATAFOLDER)/$(MODE)/encodings/ --output $(FIGURE_DIR)/$(MODE)
	$(BIN)/format_tables_count_pbs --input $(DATAFOLDER)/$(MODE)/shapes/ --output $(FIGURE_DIR)/$(MODE)


SEARCH_OUTPUT ?= $(abspath ./search/)
decompose: check-decompose-vars $(STAMP)
	$(BIN)/search-api --s $(S) --p $(P) --n $(N) --gamma $(GAMMA) --sbox_filename $(SBOX_FILE) --output $(SEARCH_OUTPUT)

check-decompose-vars:
	$(foreach v,S P N SBOX_FILE, \
		$(if $($(v)),,$(error $(v) is not set)))


reproduce: $(STAMP)
	@echo "Rerun the CJP benches"
	@$(MAKE) bench-cjp
	@echo "Rerun the TBM benches"
	@$(MAKE) bench-tbm
	@echo "Rerun the WoP-PBS benches"
	@$(MAKE) bench-woppbs
	@echo "Rerun the benches for our work"
	@$(MAKE) bench-hlut-full PERROR=40 MODE=paper
	@$(MAKE) bench-hlut-full PERROR=128 MODE=paper
	@echo "Rerun the other experiments"
	@$(MAKE) experiments
	@echo "Regenerating the Figures"
	@$(MAKE) plots MODE=regenerated
