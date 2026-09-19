import os
import shutil

# ================================
#   HẰNG SỐ — BẠN CHỈ SỬA TẠI ĐÂY
# ================================
TARGET_FOLDER = "2026_01_25_JPN_anl5_model_maaket_ok"             # thư mục copy file vào
PATH_SUBMIT_FILE = "KQ_JPN_add_anl5_20_market_25_1_26_reefresh.csv"   # file path_submit bạn muốn dùng
## IND - fun44
### maarket ok 25/1/26
# variables = ['anl15_gr_12_m_cos_dn', 'anl15_s_cal_fy2_total', 'anl15_gr_fy3_ests_dn', 'anl15_s_ltg_mdn', 'anl15_s_cal_fy1_mean', 'anl15_s_12_m_ests_up', 'anl15_s_cal_fy3_pe', 'anl15_gr_12_m_cos', 'anl15_s_cal_fy0_val', 'anl15_s_cal_fy2_mean', 'anl15_s_ltg_ests_dn', 'anl15_s_cal_fy1_pe', 'anl15_gr_12_m_mean', 'anl15_gr_12_m_1m_chg', 'anl15_s_prc', 'anl15_gr_12_m_3m_chg', 'anl15_s_cal_fy3_total', 'anl15_ind_18_m_ests_up', 'anl15_ind_fy3_ests_up', 'anl15_s_ltg_cos_up']
# ### sector
# variables = ['anl15_ind_18_m_ests', 'anl15_s_cal_fy2_total', 'anl15_gr_18_m_st_dev', 'anl15_gr_12_m_cos_up', 'anl15_s_cal_fy1_pe', 'anl15_s_12_m_cos_dn', 'anl15_ind_cal_fy1_3m_chg', 'anl15_gr_cal_fy3_total', 'anl15_gr_12_m_ests', 'anl15_gr_fy3_ests_dn', 'anl15_s_ltg_mktcap', 'anl15_s_cal_fy1_st_dev', 'anl15_s_cal_fy3_mean', 'anl15_s_cal_fy3_ests', 'anl15_s_cal_fy2_mean', 'anl15_s_18_m_total', 'anl15_s_cal_fy1_mktcap', 'anl15_s_prc', 'anl15_s_fy3_cos_up', 'anl15_s_18_m_mktcap', 'anl15_ind_fy2_ests_up', 'anl15_s_ltg_ests_dn', 'anl15_s_12_m_mean', 'anl15_gr_12_m_mean', 'anl15_ind_18_m_ests_up', 'anl15_gr_12_m_1m_chg', 'anl15_s_12_m_st_dev', 'anl15_s_18_m_cos_dn', 'anl15_s_fy1_cos_dn', 'anl15_s_cal_fy3_total', 'anl15_s_ltg_mdn', 'anl15_s_18_m_pe', 'anl15_ind_fy3_ests_up', 'anl15_s_18_m_cos_up', 'anl15_s_18_m_ests_dn', 'anl15_ind_12_m_ests_up', 'anl15_gr_fy1_ests_dn', 'anl15_s_18_m_mean', 'anl15_s_12_m_ests_up', 'anl15_s_cal_fy2_mktcap', 'anl15_s_fy1_cos_up', 'anl15_gr_12_m_3m_chg', 'anl15_s_cal_fy3_pe', 'anl15_s_ltg_ests_up', 'anl15_s_cal_fy1_total', 'anl15_s_cal_fy3_st_dev', 'anl15_s_cal_fy0_val', 'anl15_gr_fy1_ests_up', 'anl15_gr_cal_fy3_ests', 'anl15_gr_12_m_cos', 'anl15_s_hist_eps_gro', 'anl15_ind_cal_fy1_1m_chg', 'anl15_s_12_m_mktcap', 'anl15_s_cal_fy2_pe', 'anl15_s_ltg_cos', 'anl15_s_fy2_ests_dn', 'anl15_s_cal_fy3_mktcap', 'anl15_gr_12_m_ests_up', 'anl15_s_ltg_cos_up', 'anl15_ind_cal_fy1_ests', 'anl15_gr_12_m_cos_dn', 'anl15_s_cal_fy1_mean', 'anl15_gr_12_m_mktcap', 'anl15_s_cal_fy3_cos', 'anl15_gr_12_m_6m_chg', 'anl15_s_ltg_st_dev']
# variables = ['rsk70_mfm2_euetrd_shortint', 'rsk70_mfm2_euetrd_profit', 'rsk70_trsd_drteue_2mfm', 'rsk70_mfm2_euetrd_srtindcnt', 'rsk70_mfm2_euetrd_divyild', 'rsk70_mfm2_euetrd_momentum', 'rsk70_mfm2_euetrd_strevrsl', 'rsk70_mfm2_euetrd_earnqlty', 'rsk70_mfm2_euetrd_anlystsn', 'rsk70_mfm2_euetrd_srisku', 'rsk70_mfm2_euetrd_indmom', 'rsk70_mfm2_euetrd_resvol', 'rsk70_mfm2_euetrd_cntadj', 'rsk70_mfm2_euetrd_midcap', 'rsk70_mfm2_euetrd_size', 'rsk70_mfm2_euetrd_beta', 'rsk70_mfm2_euetrd_earnvar', 'rsk70_mfm2_euetrd_newssent', 'rsk70_mfm2_euetrd_indadj', 'rsk70_mfm2_euetrd_primaryindustry']

# variables = ['anl4_qfv4_eps_number', 'anl4_netprofit_median', 'anl4_epsr_low', 'anl4_afv4_cfps_mean', 'anl4_ptp_median', 'sales_estimate_average_annual', 'anl4_afv4_div_number', 'est_netprofit_adj', 'shareholders_equity_estimate_median_qf', 'est_netprofit', 'anl4_bvps_number', 'est_ebit', 'anl4_epsa_median', 'anl4_netprofita_low', 'anl4_afv4_cfps_median', 'anl4_epsa_high', 'anl4_netprofit_high', 'est_grossincome', 'sales_estimate_dispersion', 'sales_estimate_stddev_quarterly', 'earnings_per_share_adjusted_estimate_standard_deviation', 'anl4_afv4_dts_spe', 'anl4_ptpr_number', 'anl4_bvps_high', 'anl4_netprofita_median', 'anl4_ptp_number', 'anl4_median_epsreported', 'anl4_ebit_std', 'anl4_epsr_number', 'anl4_gric_high', 'sales_estimate_minimum_quarterly', 'anl4_afv4_eps_mean', 'anl4_ptp_low', 'anl4_gric_median', 'anl4_afv4_div_high', 'anl4_epsa_number', 'shareholders_equity_estimate_count_qf', 'anl4_qfv4_eps_low', 'anl4_afv4_div_median', 'anl4_ptpr_median', 'anl4_bvps_median', 'anl4_qfv4_median_eps', 'anl4_totassets_high', 'anl4_netprofita_high', 'anl4_epsr_high', 'median_sales_estimate', 'anl4_afv4_cfps_number', 'shareholders_equity_estimate_minimum_qf', 'anl4_ptpr_high', 'anl4_netprofit_number', 'anl4_ebitda_number', 'anl4_qfv4_dts_spe', 'anl4_afv4_div_std', 'anl4_netprofit_low', 'sales_estimate_count_quarterly', 'anl4_afv4_eps_number', 'anl4_qfv4_eps_high', 'lowest_sales_estimate', 'shareholders_equity_estimate_maximum_qf', 'anl4_netprofit_std', 'anl4_medianepsbfam', 'est_epsr', 'est_ebitda', 'est_ptpr', 'anl4_afv4_eps_low', 'anl4_afv4_div_low', 'est_epsa', 'anl4_totassets_median', 'anl4_afv4_eps_high', 'anl4_dts_ptp', 'anl4_totassets_low', 'anl4_ebit_median', 'anl4_ptpr_low', 'anl4_afv4_div_mean', 'est_bookvalue_ps', 'est_tot_assets', 'anl4_totassets_number', 'anl4_ebit_number', 'anl4_epsa_low', 'anl4_afv4_median_eps', 'reporting_currency_code_9', 'net_income_adjusted_estimate_standard_deviation', 'anl4_qfv4_eps_mean', 'anl4_gric_low', 'anl4_afv4_cfps_low', 'anl4_ebit_high', 'shareholders_equity_estimate_average_qf', 'anl4_ebit_low', 'anl4_gric_number', 'sales_estimate_average_quarterly', 'anl4_netprofita_number', 'sales_estimate_maximum_quarterly', 'anl4_afv4_cfps_high', 'highest_sales_estimate', 'sales_estimate_count_2', 'sales_estimate_median_quarterly', 'anl4_ebitda_std', 'anl4_ptp_high', 'anl4_bvps_low', 'anl4_ebitda_high', 'anl4_ebitda_low', 'est_ptp']

# variables = ['anl15_gr_12_m_1m_chg', 'anl15_gr_12_m_3m_chg', 'anl15_gr_12_m_cos', 'anl15_gr_12_m_cos_dn', 'anl15_gr_12_m_cos_up', 'anl15_gr_12_m_ests', 'anl15_gr_12_m_ests_up', 'anl15_gr_12_m_mean', 'anl15_gr_12_m_mktcap', 'anl15_gr_18_m_st_dev', 'anl15_gr_cal_fy3_ests', 'anl15_gr_cal_fy3_total', 'anl15_gr_fy1_ests_dn', 'anl15_gr_fy1_ests_up', 'anl15_gr_fy3_ests_dn', 'anl15_ind_12_m_ests_up', 'anl15_ind_18_m_ests', 'anl15_ind_18_m_ests_up', 'anl15_ind_cal_fy1_1m_chg', 'anl15_ind_cal_fy1_3m_chg', 'anl15_ind_cal_fy1_ests', 'anl15_ind_fy2_ests_up', 'anl15_ind_fy3_ests_up', 'anl15_s_12_m_ests_up', 'anl15_s_12_m_mean', 'anl15_s_12_m_mktcap', 'anl15_s_18_m_cos_dn', 'anl15_s_18_m_ests_dn', 'anl15_s_18_m_mean', 'anl15_s_18_m_mktcap', 'anl15_s_18_m_pe', 'anl15_s_18_m_total', 'anl15_s_cal_fy0_val', 'anl15_s_cal_fy1_mean', 'anl15_s_cal_fy1_mktcap', 'anl15_s_cal_fy1_pe', 'anl15_s_cal_fy1_st_dev', 'anl15_s_cal_fy1_total', 'anl15_s_cal_fy2_mean', 'anl15_s_cal_fy2_mktcap', 'anl15_s_cal_fy2_pe', 'anl15_s_cal_fy2_total', 'anl15_s_cal_fy3_cos', 'anl15_s_cal_fy3_ests', 'anl15_s_cal_fy3_mean', 'anl15_s_cal_fy3_mktcap', 'anl15_s_cal_fy3_pe', 'anl15_s_cal_fy3_st_dev', 'anl15_s_cal_fy3_total', 'anl15_s_fy1_cos_dn', 'anl15_s_fy1_cos_up', 'anl15_s_fy2_ests_dn', 'anl15_s_fy3_cos_up', 'anl15_s_hist_eps_gro', 'anl15_s_ltg_cos_up', 'anl15_s_ltg_ests_dn', 'anl15_s_ltg_ests_up', 'anl15_s_ltg_mdn', 'anl15_s_ltg_mktcap', 'anl15_s_ltg_st_dev', 'anl15_s_prc']

### MEA
# variables = ['adjfactor', 'adv20', 'dividend', 'returns', 'cap', 'close', 'high', 'low', 'open', 'sharesout', 'split', 'volume', 'vwap']
# variables = ['mdl25_eq_rd_v5', 'mdl25_eq_pc_v19', 'mdl25_eq_cfs_v16', 'mdl25_eq_cb_v27', 'mdl25_eq_pc_v22', 'mdl25_eq_cfs_v9', 'mdl25_eq_bs_v10', 'mdl25_eq_pc_v23', 'mdl25_eq_pc_v8', 'mdl25_eq_cfs_v8', 'exclusions_component_score_cb', 'mdl25_eq_rp_v13', 'mdl25_eq_vr_v19', 'mdl25_eq_rlev_v9', 'mdl25_eq_cb_v21', 'mdl25_eq_pc_v25', 'mdl25_eq_is_v31', 'mdl25_eq_vr_v5', 'mdl25_eq_v12', 'mdl25_eq_rd_v18', 'mdl25_eq_rlev_v5', 'mdl25_eq_cb_v7', 'mdl25_eq_pc_v27', 'mdl25_eq_pc_v34', 'mdl25_eq_rp_v7', 'mdl25_eq_rd_v15', 'mdl25_eq_rlev_v12', 'mdl25_eq_is_v28', 'mdl25_eq_is_v44', 'mdl25_eq_rliq_v12', 'mdl25_eq_is_v45', 'mdl25_eq_rlev_v8', 'mdl25_eq_cfs_v6', 'mdl25_eq_vr_v12', 'mdl25_eq_cfs_v11', 'mdl25_eq_is_v6', 'mdl25_eq_ro_v9', 'mdl25_eq_cfs_v5', 'mdl25_eq_v17', 'mdl25_eq_pc_v11', 'earnings_quality_score_cb_01', 'mdl25_eq_vr_v17', 'mdl25_eq_cfs_v14', 'mdl25_eq_is_v47', 'mdl25_eq_is_v32', 'mdl25_eq_is_v13', 'mdl25_eq_cb_v11', 'mdl25_eq_rd_v7', 'mdl25_eq_rliq_v11', 'mdl25_eq_is_v25', 'mdl25_eq_is_v35', 'mdl25_eq_pc_v10', 'earnings_quality_score_current_cb', 'mdl25_eq_vr_v11', 'mdl25_eq_rliq_v8', 'mdl25_eq_cb_v22', 'mdl25_eq_ro_v17', 'mdl25_eq_rlev_v6', 'mdl25_eq_pc_v18', 'mdl25_eq_pc_v21', 'earnings_quality_score_current', 'mdl25_eq_ro_v19', 'accruals_component_score', 'mdl25_eq_rliq_v5', 'mdl25_eq_vr_v9', 'mdl25_eq_rp_v10', 'mdl25_eq_is_v34', 'mdl25_eq_pc_v35', 'mdl25_eq_cfs_v10', 'earnings_quality_score_change_1_day', 'mdl25_eq_ro_v11', 'mdl25_eq_rd_v13', 'mdl25_eq_rd_v10', 'mdl25_eq_v9', 'mdl25_eq_rlev_v7', 'mdl25_eq_rlev_v11', 'mdl25_eq_is_v30', 'mdl25_eq_v7', 'mdl25_eq_vr_v13', 'mdl25_eq_rp_v9', 'mdl25_eq_cb_v9', 'mdl25_eq_cfs_v7', 'mdl25_eq_v22', 'mdl25_eq_is_v7', 'mdl25_eq_is_v12', 'mdl25_eq_bs_v7', 'mdl25_eq_rd_v20', 'mdl25_eq_is_v10', 'earnings_quality_score_raw_cb', 'mdl25_eq_pc_v15', 'mdl25_eq_is_v11', 'mdl25_eq_is_v18', 'mdl25_eq_pc_v17', 'mdl25_eq_vr_v6', 'mdl25_eq_cfs_v15', 'mdl25_eq_bs_v5', 'mdl25_eq_rp_v16', 'mdl25_eq_is_v9', 'mdl25_eq_pc_v9', 'mdl25_eq_rp_v17', 'earnings_quality_score_raw', 'mdl25_eq_v16', 'mdl25_eq_is_v14', 'mdl25_eq_is_v33', 'mdl25_eq_rp_v20', 'mdl25_eq_is_v51', 'mdl25_eq_is_v5', 'mdl25_eq_rliq_v7', 'mdl25_eq_rp_v8', 'mdl25_eq_pc_v26', 'mdl25_eq_is_v26', 'mdl25_eq_cfs_v19', 'mdl25_eq_cb_v20', 'mdl25_eq_is_v27', 'mdl25_eq_cfs_v12', 'mdl25_eq_bs_v6', 'earnings_quality_score_cb', 'earnings_quality_score_change_1_day_cb', 'mdl25_eq_ro_v20', 'mdl25_eq_is_v43', 'mdl25_eq_ro_v13', 'mdl25_eq_rd_v17', 'mdl25_eq_rd_v11', 'mdl25_eq_pc_v6', 'mdl25_eq_rd_v8', 'mdl25_eq_is_v49', 'mdl25_eq_ro_v14', 'earnings_quality_score_3', 'mdl25_eq_pc_v29', 'mdl25_eq_is_v8', 'mdl25_eq_ro_v16', 'mdl25_eq_is_v37', 'mdl25_eq_vr_v7', 'mdl25_eq_ro_v10', 'mdl25_eq_bs_v12', 'mdl25_eq_v6', 'mdl25_eq_is_v24', 'mdl25_eq_pc_v13', 'mdl25_eq_rp_v19', 'mdl25_eq_rd_v14', 'mdl25_eq_pc_v24', 'cash_flow_component_score', 'mdl25_eq_vr_v16', 'mdl25_eq_ro_v12', 'mdl25_eq_is_v48', 'mdl25_eq_ro_v21', 'mdl25_eq_rp_v18', 'exclusions_component_score', 'mdl25_eq_cb_v8', 'mdl25_eq_ro_v5', 'mdl25_eq_ro_v22', 'mdl25_eq_rp_v11', 'mdl25_eq_v14', 'mdl25_eq_vr_v15', 'operating_efficiency_component_score', 'mdl25_eq_rliq_v10', 'mdl25_eq_rd_v9', 'mdl25_eq_v13', 'mdl25_eq_v18', 'accruals_component_score_cb', 'mdl25_eq_vr_v14', 'mdl25_eq_pc_v7', 'mdl25_eq_is_v17', 'mdl25_eq_rp_v15', 'mdl25_eq_rd_v19', 'mdl25_eq_rp_v14', 'mdl25_eq_rliq_v9', 'mdl25_eq_pc_v5', 'mdl25_eq_cb_v10', 'mdl25_eq_cb_v23', 'operating_efficiency_component_score_cb', 'mdl25_eq_pc_v31', 'mdl25_eq_pc_v14', 'mdl25_eq_vr_v10', 'mdl25_eq_v8', 'mdl25_eq_cb_v12', 'mdl25_eq_v10', 'mdl25_eq_pc_v16', 'mdl25_eq_ro_v6', 'mdl25_eq_bs_v9', 'mdl25_eq_pc_v30', 'mdl25_eq_rp_v12', 'mdl25_eq_bs_v13', 'mdl25_eq_bs_v19', 'mdl25_eq_ro_v15', 'mdl25_eq_cb_v6', 'cash_flow_component_score_cb', 'mdl25_eq_is_v39', 'mdl25_eq_rd_v6', 'mdl25_eq_pc_v20', 'mdl25_eq_pc_v33', 'mdl25_eq_bs_v11', 'mdl25_eq_vr_v18', 'mdl25_eq_is_v16', 'mdl25_eq_ro_v8', 'mdl25_eq_ro_v18', 'mdl25_eq_bs_v8', 'mdl25_eq_is_v38', 'mdl25_eq_pc_v12', 'mdl25_eq_is_v15', 'mdl25_eq_pc_v32', 'mdl25_eq_pc_v28', 'mdl25_eq_rd_v12', 'mdl25_eq_rlev_v10', 'mdl25_eq_rliq_v6', 'mdl25_eq_is_v46', 'mdl25_eq_ro_v7', 'mdl25_eq_rd_v16', 'mdl25_eq_rp_v6', 'mdl25_eq_is_v50', 'mdl25_eq_cfs_v13', 'mdl25_eq_rp_v5', 'mdl25_eq_vr_v8', 'mdl25_eq_is_v29']

## DEU model38
variables = ['star_val_dividend_projection_fy1', 'region_rank_price_to_intrinsic_value', 'star_val_earnings_projection_fy1', 'sector_rank_price_to_intrinsic_value', 'pe_ratio_relative_score', 'ev_ebitda_relative_score', 'star_val_dividend_projection_fy9', 'star_val_dividend_projection_fy3', 'mdl38_iv_growth_ear', 'star_val_piv_industry_rank', 'star_val_dividend_projection_fy2', 'star_val_earnings_projection_fy2', 'star_val_piv_ratio', 'star_val_ev_sales', 'mdl38_iv_div_payout_rate', 'star_val_earnings_projection_fy4', 'star_val_pb', 'star_val_earnings_projection_fy14', 'star_val_pcf', 'star_val_iv_projection', 'star_val_earnings_projection_fy8', 'star_val_buyback_yield', 'star_val_earnings_projection_fy11', 'star_val_dividend_projection_fy10', 'star_val_earnings_projection_fy7', 'region_relative_valuation_rank', 'star_val_sector_rank', 'star_val_industry_rank', 'star_val_dividend_projection_fy13', 'star_val_earnings_projection_fy3', 'star_val_dividend_yield', 'star_val_dividend_projection_fy4', 'mdl38_iv_cagr_base_year', 'star_val_piv_region_rank', 'buyback_yield_relative_component_rank_d1', 'mdl38_iv_warranted_f12m_p_e', 'star_val_dividend_projection_fy15', 'industry_relative_valuation_rank', 'star_val_region_rank', 'star_val_earnings_projection_fy13', 'star_val_implied10_eps_cagr', 'star_val_fwd5_eps_cagr', 'star_val_pe', 'mdl38_iv_discount_rate', 'star_val_dividend_projection_fy14', 'star_val_dividend_projection_fy5', 'star_val_earnings_projection_fy15', 'long_term_assumed_annual_earnings', 'star_val_dividend_projection_fy6', 'star_val_implied5_eps_cagr', 'mdl38_iv_year_div', 'relative_valuation_global_position_d1', 'mdl38_rel_val_ev_ebitda', 'star_val_earnings_projection_fy9', 'dividend_yield_relative_component_rank_d1', 'price_to_intrinsic_value_industry_position_d1', 'star_val_dividend_projection_fy7', 'mdl38_rel_val_global_rk', 'star_val_earnings_projection_fy10', 'sector_relative_valuation_rank', 'star_val_earnings_projection_fy5', 'star_val_fwd10_eps_cagr', 'star_val_dividend_projection_fy11', 'ev_sales_relative_component_rank_d1', 'pcf_ratio_relative_component_rank_d1', 'star_val_dividend_projection_fy12', 'star_val_earnings_projection_fy6', 'star_val_piv_sector_rank', 'star_val_dividend_projection_fy8', 'star_val_earnings_projection_fy12', 'pb_ratio_relative_component_rank_d1']

# FILES = [
#     "alpha.txt",
#     "alpha_pass.txt",
#     "alpha_false.txt",
#     "config.json",
#     "loc.csv",
#     PATH_SUBMIT_FILE               # file path_submit
# ]

# # Tạo thư mục test/doi
# DEST_FOLDER = f"{TARGET_FOLDER}/doi"
# os.makedirs(DEST_FOLDER, exist_ok=True)

# # Copy các file vào thư mục test/doi
# for f in FILES:
#     if os.path.exists(f):
#         shutil.copy(f, DEST_FOLDER)
#         print(f"Đã copy: {f} → {DEST_FOLDER}")
#     else:
#         print(f"[WARN] Không tìm thấy file: {f}")
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
alpha_single = os.path.join(CURRENT_DIR, "alpha_single.txt")
alpha_pass_single = os.path.join(CURRENT_DIR, "alpha_pass_single.txt")
alpha_false_single = os.path.join(CURRENT_DIR, "alpha_false_single.txt")

# Xóa nội dung 3 file trong thư mục hiện tại
for clear_file in [alpha_single, alpha_pass_single, alpha_false_single]:
    if os.path.exists(clear_file):
        open(clear_file, "w").close()
        print(f"Đã xóa nội dung file: {clear_file}")
    else:
        print(f"[WARN] Không tìm thấy file để xóa nội dung: {clear_file}")

print("\nHoàn thành!")
import random
import re

# Chuyển từ operator gốc sang cấu trúc generator mới; không dùng operators_one_var_ts
DAYS=[20,40,60,90,120,252]
DAY_WEIGHTS=[10,20,15,20,20,15]
GROUPS=["subindustry","industry","sector","market"]

operators_one_var_base=[
    'abs({})',
    'days_from_last_change({})',
    'group_backfill({}, group, D, std = 4.0)',
    'group_extra({}, weight, group)',
    'group_mean({}, weight, group)',
    'group_neutralize({}, group)',
    'group_rank({}, group)',
    'group_scale({}, group)',
    'group_zscore({}, group)',
    'hump({}, hump = 0.01)',
    'inverse({})',
    'kth_element({}, D, k=1)',
    'last_diff_value({}, D)',
    'log({})',
    'normalize({}, useStd = false, limit = 0.0)',
    'quantile({}, driver = gaussian, sigma = 1.0)',
    'reverse({})',
    'scale({}, scale=1, longscale=1, shortscale=1)',
    'sigmoid({})',
    'sign({})',
    'sqrt({})',
    'tanh({})',
    'ts_arg_max({}, D)',
    'ts_arg_min({}, D)',
    'ts_av_diff({}, D)',
    'ts_backfill({}, D)',
    'ts_count_nans({} ,D)',
    'ts_decay_linear({}, D, dense = false)',
    'ts_delay({}, D)',
    'ts_delta({}, D)',
    'ts_entropy({},D)',
    'ts_mean({}, D)',
    'ts_min_diff({}, D)',
    'ts_min_max_cps({}, D, f = 2)',
    'ts_min_max_diff({}, D, f = 0.5)',
    'ts_product({}, D)',
    'ts_quantile({},D, driver=',
    'ts_rank({}, D, constant = 0)',
    'ts_scale({}, D, constant = 0)',
    'ts_skewness({}, D)',
    'ts_std_dev({}, D)',
    'ts_sum({}, D)',
    'ts_target_tvr_decay({}, lambda_min=0, lambda_max=1, target_tvr=0.1)',
    'ts_zscore({}, D)',
    'winsorize({}, std=4)',
    'zscore({})'
]

operators_one_var_priority=[
    'group_neutralize({}, group)',
    'group_rank({}, group)',
    'group_zscore({}, group)',
    'normalize({}, useStd = false, limit = 0.0)',
    'ts_backfill({}, D)',
    'ts_decay_linear({}, D, dense = false)',
    'ts_delay({}, D)',
    'ts_delta({}, D)',
    'ts_mean({}, D)',
    'ts_rank({}, D, constant = 0)',
    'ts_std_dev({}, D)',
    'ts_zscore({}, D)',
    'winsorize({}, std=4)',
    'zscore({})','ts_count_nans({}, D)','days_from_last_change({})'
]

operators_one_var=operators_one_var_base+operators_one_var_priority*2

operators_two_var=[
    'add({}, {}, filter = false)',
    'divide({}, {})',
    'max({}, {})',
    'min({}, {})',
    'multiply({} ,{},filter=false)',
    'power({}, {})',
    'regression_proj({}, {})',
    'signed_power({}, {})',
    'subtract({}, {}, filter=false)',
    'ts_corr({}, {}, D)',
    'ts_covariance({}, {}, D)',
    'ts_regression({}, {}, D, lag = 0, rettype = 0)',
    'vector_proj({}, {})'
]

operators_three_var=[
    'trade_when({}, {}, {})'
]

math_operators=["*","/","^","+","-"]

P_ONE=0.80
P_TWO=0.18
P_THREE=0.02
P_MATH=0.20
P_FINAL_RANK=1.00

def choose_day():
    return random.choices(DAYS,weights=DAY_WEIGHTS,k=1)[0]

def fill_params(template):
    if re.search(r"\bD\b",template):
        template=re.sub(r"\bD\b",str(choose_day()),template)
    if re.search(r"\bweight\b",template):
        template=re.sub(r"\bweight\b",str(random.choice([round(i*0.1,1) for i in range(1,10)])),template)
    if re.search(r"\bgroup\b",template):
        template=re.sub(r"\bgroup\b",random.choice(GROUPS),template)
    return template

def other_variable(variable):
    pool=[x for x in variables if x!=variable]
    return random.choice(pool) if pool else variable

def unary(expr):
    return fill_params(random.choice(operators_one_var).format(expr))

def second_branch(variable,source=None):
    v=other_variable(variable)
    expr=v if random.random()<0.35 else unary(v)
    if source is not None and expr==source:
        expr=unary(v)
    return expr

def binary(left,right):
    return fill_params(random.choice(operators_two_var).format(left,right))

def generate_nested_formula(variable,depth,apply_math_layer):
    formula_stack=[variable]
    for i in range(depth):
        current=formula_stack[-1]
        r=random.random()
        if r<P_ONE:
            new_formula=unary(current)
        elif r<P_ONE+P_TWO:
            new_formula=binary(current,second_branch(variable,current))
        else:
            trigger=second_branch(variable,current)
            exit_expr=second_branch(variable,current)
            new_formula=fill_params(random.choice(operators_three_var).format(trigger,current,exit_expr))
        formula_stack.append(new_formula)
        if i==apply_math_layer:
            right=second_branch(variable,formula_stack[-1])
            formula_stack[-1]=f"({formula_stack[-1]}){random.choice(math_operators)}({right})"
    return formula_stack[-1]

configs=[
    {"NESTED_DEPTH":2,"LIMIT":30000},
    {"NESTED_DEPTH":3,"LIMIT":45000},
    {"NESTED_DEPTH":4,"LIMIT":25000},
]

all_formulas=set()
for cfg in configs:
    NESTED_DEPTH=cfg["NESTED_DEPTH"]
    LIMIT=cfg["LIMIT"]
    formulas=set()
    attempts=0
    max_attempts=LIMIT*20
    while len(formulas)<LIMIT and attempts<max_attempts:
        attempts+=1
        var=random.choice(variables)
        math_layer=random.randrange(NESTED_DEPTH) if random.random()<P_MATH else None
        formula=generate_nested_formula(var,NESTED_DEPTH,math_layer)
        if random.random()<P_FINAL_RANK:
            formula=f"rank({formula})"
        if formula not in all_formulas:
            formulas.add(formula)
            all_formulas.add(formula)
    with open(alpha_single,"a",encoding="utf-8") as f:
        f.write("\n".join(formulas)+("\n" if formulas else ""))
    print(f"✅ Depth {NESTED_DEPTH}: đã tạo {len(formulas):,}/{LIMIT:,} công thức unique.")

with open(alpha_single,"r",encoding="utf-8") as f:
    alpha_list=[line.strip() for line in f if line.strip()]
random.shuffle(alpha_list)
with open(alpha_single,"w",encoding="utf-8") as f:
    f.write("\n".join(alpha_list)+("\n" if alpha_list else ""))
print(f"✅ Tổng {len(alpha_list):,} công thức unique; đã random thứ tự thành công!")
