import logging
import os
from math import log2

import pandas as pd

DATA = pd.read_csv(
    os.path.join(
        os.path.dirname(__file__), "../../../../parameters/optimizer_cjp_odd-128.csv"
    ),
    header=0,
    sep=",",
)


def select_and_format_parameters(p, norm):
    # round norm to the closest power of two
    # row = DATA[(DATA['p'] == p) & (DATA['nu'] == closest_norm) ].to_dict(orient='list')
    row = DATA[DATA["nu"] >= norm].to_dict(orient="list")
    if not (len(row["nu"])):
        logging.error("No parameters found for p=%d and norm=%d", p, norm)
    norm_parameters = row["nu"][0]
    # return (
    #     f"""let parameters = BooleanParameters{{
    #     lwe_dimension: LweDimension({row["n"][0]}),
    #     glwe_dimension: GlweDimension({row["k"][0]}),
    #     polynomial_size: PolynomialSize({row["N"][0]}),
    #     lwe_modular_std_dev: StandardDev({row["sigma_lwe"][0]}),
    #     glwe_modular_std_dev: StandardDev({row["sigma_glwe"][0]}),
    #     pbs_base_log: DecompositionBaseLog({int(log2(row["b_bs"][0]))}),
    #     pbs_level: DecompositionLevelCount({row["l_bs"][0]}),
    #     ks_base_log: DecompositionBaseLog({int(log2(row["b_ks"][0]))}),
    #     ks_level: DecompositionLevelCount({row["l_ks"][0]}),
    #     encryption_key_choice: EncryptionKeyChoice::Big,
    # }};\n""",
    #     norm_parameters,
    # )
    return norm_parameters
