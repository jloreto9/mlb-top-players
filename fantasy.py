import pandas as pd
import numpy as np
from constants import FANTASY_SCORING_PRESETS, PARK_FACTORS, LOWER_IS_BETTER

def calculate_batting_fantasy(df: pd.DataFrame, scoring_preset: str = 'ESPN Standard', min_pa: int = 50) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if 'Team' not in out.columns and 'Tm' in out.columns:
        out['Team'] = out['Tm']
    if 'AVG' not in out.columns and 'BA' in out.columns:
        out['AVG'] = out['BA']
    if 'K' not in out.columns and 'SO' in out.columns:
        out['K'] = out['SO']
    elif 'SO' not in out.columns and 'K' in out.columns:
        out['SO'] = out['K']

    num_cols = ['PA', 'AB', 'H', '1B', '2B', '3B', 'HR', 'R', 'RBI', 'BB', 'HBP', 'SO', 'K', 'SB', 'CS', 'AVG', 'OBP', 'SLG', 'wOBA', 'xBA', 'xSLG', 'xwOBA', 'HardHit%', 'Barrel%', 'EV', 'maxEV', 'CSW%', 'WAR']
    for c in num_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors='coerce')

    if '1B' not in out.columns or out['1B'].isna().all():
        if all(c in out.columns for c in ['H', '2B', '3B', 'HR']):
            out['1B'] = (out['H'].fillna(0) - out['2B'].fillna(0) - out['3B'].fillna(0) - out['HR'].fillna(0)).clip(lower=0)
        else:
            out['1B'] = out.get('H', 0)

    if 'xBA' in out.columns and 'AVG' in out.columns:
        out['diff_BA'] = (pd.to_numeric(out['AVG'], errors='coerce') - pd.to_numeric(out['xBA'], errors='coerce')).round(3)
    if 'xSLG' in out.columns and 'SLG' in out.columns:
        out['diff_SLG'] = (pd.to_numeric(out['SLG'], errors='coerce') - pd.to_numeric(out['xSLG'], errors='coerce')).round(3)
    if 'xwOBA' in out.columns and 'wOBA' in out.columns:
        out['diff_wOBA'] = (pd.to_numeric(out['wOBA'], errors='coerce') - pd.to_numeric(out['xwOBA'], errors='coerce')).round(3)

    preset = FANTASY_SCORING_PRESETS.get(scoring_preset, FANTASY_SCORING_PRESETS['ESPN Standard'])['batting']
    pts = pd.Series(0.0, index=out.index)
    for stat, weight in preset.items():
        if stat in out.columns:
            pts += out[stat].fillna(0) * weight
    out['Fantasy_Pts'] = pts.round(1)

    qual_mask = out.get('PA', pd.Series(0, index=out.index)).fillna(0) >= min_pa
    pool = out[qual_mask] if qual_mask.sum() >= 10 else out

    cat_cols = ['R', 'HR', 'RBI', 'SB', 'AVG']
    z_cols = []
    for cat in cat_cols:
        z_name = f'z_{cat}'
        z_cols.append(z_name)
        if cat in out.columns:
            mean = pool[cat].mean()
            std = pool[cat].std()
            if pd.notna(std) and std > 0:
                out[z_name] = ((out[cat] - mean) / std).round(2)
            else:
                out[z_name] = 0.0
        else:
            out[z_name] = 0.0

    out['z_Total'] = out[z_cols].sum(axis=1).round(2)
    out['Fantasy_Rank'] = out['z_Total'].rank(ascending=False, method='min').astype(int)
    return out

def calculate_pitching_fantasy(df: pd.DataFrame, scoring_preset: str = 'ESPN Standard', min_ip: int = 20) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if 'Team' not in out.columns and 'Tm' in out.columns:
        out['Team'] = out['Tm']
    if 'K' not in out.columns and 'SO' in out.columns:
        out['K'] = out['SO']
    elif 'SO' not in out.columns and 'K' in out.columns:
        out['SO'] = out['K']

    num_cols = ['W', 'L', 'G', 'GS', 'SV', 'BS', 'HLD', 'IP', 'H', 'ER', 'HR', 'BB', 'SO', 'K', 'ERA', 'WHIP', 'FIP', 'xFIP', 'SIERA', 'xERA', 'Stuff+', 'Location+', 'Pitching+', 'K%', 'BB%', 'K-BB%', 'CSW%', 'WAR']
    for c in num_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors='coerce')

    if 'xERA' in out.columns and 'ERA' in out.columns:
        out['diff_ERA'] = out['ERA'] - out['xERA']

    preset = FANTASY_SCORING_PRESETS.get(scoring_preset, FANTASY_SCORING_PRESETS['ESPN Standard'])['pitching']
    pts = pd.Series(0.0, index=out.index)
    for stat, weight in preset.items():
        if stat in out.columns:
            pts += out[stat].fillna(0) * weight
    out['Fantasy_Pts'] = pts.round(1)

    qual_mask = out.get('IP', pd.Series(0, index=out.index)).fillna(0) >= min_ip
    pool = out[qual_mask] if qual_mask.sum() >= 10 else out

    for cat in ['W', 'SV', 'SO']:
        z_name = f'z_{cat}'
        if cat in out.columns:
            mean = pool[cat].mean()
            std = pool[cat].std()
            out[z_name] = (((out[cat] - mean) / std) if pd.notna(std) and std > 0 else 0.0).round(2)
        else:
            out[z_name] = 0.0

    for cat in ['ERA', 'WHIP']:
        z_name = f'z_{cat}'
        if cat in out.columns:
            mean = pool[cat].mean()
            std = pool[cat].std()
            out[z_name] = (((mean - out[cat]) / std) if pd.notna(std) and std > 0 else 0.0).round(2)
        else:
            out[z_name] = 0.0

    z_cols = ['z_W', 'z_SV', 'z_SO', 'z_ERA', 'z_WHIP']
    out['z_Total'] = out[z_cols].sum(axis=1).round(2)
    out['Fantasy_Rank'] = out['z_Total'].rank(ascending=False, method='min').astype(int)
    return out

def get_buy_low_sell_high(df_bat: pd.DataFrame, df_pit: pd.DataFrame, min_pa: int = 80, min_ip: int = 30) -> dict[str, pd.DataFrame]:
    results = {}
    if not df_bat.empty:
        bat_qual = df_bat[df_bat.get('PA', pd.Series(0, index=df_bat.index)).fillna(0) >= min_pa].copy()
        if 'diff_wOBA' not in bat_qual.columns and 'xwOBA' in bat_qual.columns and 'wOBA' in bat_qual.columns:
            bat_qual['diff_wOBA'] = (pd.to_numeric(bat_qual['wOBA'], errors='coerce') - pd.to_numeric(bat_qual['xwOBA'], errors='coerce')).round(3)

        if 'diff_wOBA' in bat_qual.columns:
            buy_bat = bat_qual[bat_qual['diff_wOBA'] <= -0.015].sort_values('diff_wOBA', ascending=True).copy()
            buy_bat['Status'] = '🟢 Comprar Barato (Mala Suerte / Rendimiento por debajo de lo esperado)'
            sell_bat = bat_qual[bat_qual['diff_wOBA'] >= 0.015].sort_values('diff_wOBA', ascending=False).copy()
            sell_bat['Status'] = '🔴 Vender Alto (Rendimiento por encima de lo esperado / Regresión)'
            results['bat_buy_low'] = buy_bat
            results['bat_sell_high'] = sell_bat
        else:
            results['bat_buy_low'] = pd.DataFrame()
            results['bat_sell_high'] = pd.DataFrame()
    else:
        results['bat_buy_low'] = pd.DataFrame()
        results['bat_sell_high'] = pd.DataFrame()

    if not df_pit.empty:
        pit_qual = df_pit[df_pit.get('IP', pd.Series(0, index=df_pit.index)).fillna(0) >= min_ip].copy()
        if 'diff_ERA' not in pit_qual.columns and 'xERA' in pit_qual.columns and 'ERA' in pit_qual.columns:
            pit_qual['diff_ERA'] = (pit_qual['ERA'] - pit_qual['xERA']).round(2)

        if 'diff_ERA' in pit_qual.columns:
            buy_pit = pit_qual[pit_qual['diff_ERA'] >= 0.35].sort_values('diff_ERA', ascending=False).copy()
            buy_pit['Status'] = '🟢 Comprar Barato (ERA inflado por mala suerte)'
            sell_pit = pit_qual[pit_qual['diff_ERA'] <= -0.35].sort_values('diff_ERA', ascending=True).copy()
            sell_pit['Status'] = '🔴 Vender Alto (ERA engañoso / regresión esperada)'
            results['pit_buy_low'] = buy_pit
            results['pit_sell_high'] = sell_pit
        else:
            results['pit_buy_low'] = pd.DataFrame()
            results['pit_sell_high'] = pd.DataFrame()
    else:
        results['pit_buy_low'] = pd.DataFrame()
        results['pit_sell_high'] = pd.DataFrame()
    return results

def evaluate_sp_matchups(schedule_df: pd.DataFrame, pit_df: pd.DataFrame, tbat_df: pd.DataFrame) -> pd.DataFrame:
    if schedule_df.empty:
        return pd.DataFrame()

    opp_strength = {}
    if not tbat_df.empty:
        tb_copy = tbat_df.copy()
        if 'Team' not in tb_copy.columns and 'Tm' in tb_copy.columns:
            tb_copy['Team'] = tb_copy['Tm']
        if 'Team' in tb_copy.columns:
            for _, row in tb_copy.iterrows():
                tm = str(row['Team']).upper()
                wrc = pd.to_numeric(row.get('wRC+', 100), errors='coerce')
                opp_strength[tm] = 100.0 if pd.isna(wrc) else float(wrc)

    pit_map = {}
    if not pit_df.empty and 'Name' in pit_df.columns:
        for _, row in pit_df.iterrows():
            name = row['Name']
            pit_map[name] = {
                'K%': pd.to_numeric(row.get('K%', 0.20), errors='coerce'),
                'BB%': pd.to_numeric(row.get('BB%', 0.08), errors='coerce'),
                'ERA': pd.to_numeric(row.get('ERA', 4.20), errors='coerce'),
                'xERA': pd.to_numeric(row.get('xERA', 4.20), errors='coerce'),
                'SIERA': pd.to_numeric(row.get('SIERA', 4.20), errors='coerce'),
                'WHIP': pd.to_numeric(row.get('WHIP', 1.30), errors='coerce'),
                'Stuff+': pd.to_numeric(row.get('Stuff+', 100), errors='coerce'),
                'Team': row.get('Team', row.get('Tm', '')),
            }

    eval_rows = []
    for _, row in schedule_df.iterrows():
        game_date = row['Date']
        away_team = row.get('Away_Abbr', '')
        home_team = row.get('Home_Abbr', '')
        sp_away = row.get('SP_Away', 'TBD')
        sp_home = row.get('SP_Home', 'TBD')
        venue = row.get('Venue', '')

        if sp_away and sp_away != 'TBD':
            eval_rows.append(_score_sp(sp_away, away_team, home_team, venue, 'Away', game_date, pit_map, opp_strength))
        if sp_home and sp_home != 'TBD':
            eval_rows.append(_score_sp(sp_home, home_team, away_team, venue, 'Home', game_date, pit_map, opp_strength))

    df_eval = pd.DataFrame(eval_rows)
    if not df_eval.empty:
        sp_counts = df_eval['Pitcher'].value_counts()
        df_eval['Two_Start'] = df_eval['Pitcher'].map(lambda name: '⭐ 2-Starts' if sp_counts.get(name, 0) >= 2 else '1 Start')
        df_eval = df_eval.sort_values('Streamer_Score', ascending=False).reset_index(drop=True)
    return df_eval

def _score_sp(pitcher_name: str, pitcher_team: str, opp_team: str, venue: str, location: str, game_date: str, pit_map: dict, opp_strength: dict) -> dict:
    p_info = pit_map.get(pitcher_name, {})
    score = 50.0
    k_pct = p_info.get('K%', 0.21)
    if pd.isna(k_pct): k_pct = 0.21
    if k_pct <= 1.0: k_pct *= 100.0
    score += (k_pct - 22.0) * 1.2

    era = p_info.get('ERA', 4.10)
    if pd.isna(era): era = 4.10
    score += (4.20 - era) * 4.0

    whip = p_info.get('WHIP', 1.28)
    if pd.isna(whip): whip = 1.28
    score += (1.30 - whip) * 20.0

    opp_wrc = opp_strength.get(opp_team.upper(), 100.0)
    score += (100.0 - opp_wrc) * 0.5

    park_f = PARK_FACTORS.get(opp_team.upper() if location == 'Away' else pitcher_team.upper(), 100.0)
    score += (100.0 - park_f) * 0.4

    if location == 'Home':
        score += 3.0

    final_score = int(np.clip(round(score), 10, 99))
    if final_score >= 80:
        tier = '🟢 Must-Start'
    elif final_score >= 65:
        tier = '🟢 Buen Stream'
    elif final_score >= 50:
        tier = '🟡 Opcional / Riesgo'
    else:
        tier = '🔴 Evitar (Sit)'

    return {
        'Date': game_date,
        'Pitcher': pitcher_name,
        'Team': pitcher_team,
        'Opponent': f'vs {opp_team}' if location == 'Home' else f'@ {opp_team}',
        'Location': location,
        'Park': venue,
        'ERA': era,
        'WHIP': whip,
        'K%': k_pct / 100.0,
        'Opp_wRC+': opp_wrc,
        'Streamer_Score': final_score,
        'Verdict': tier,
    }

def _safe_int(val, default: int = 0) -> int:
    if pd.isna(val):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def get_bullpen_depth_chart(df_pit: pd.DataFrame) -> pd.DataFrame:
    if df_pit.empty:
        return pd.DataFrame()
    out = df_pit.copy()
    if 'Team' not in out.columns and 'Tm' in out.columns:
        out['Team'] = out['Tm']
    elif 'Team' not in out.columns:
        out['Team'] = 'UNK'

    for c in ['SV', 'HLD', 'BS', 'ERA', 'WHIP', 'K%', 'BB%', 'Stuff+', 'IP', 'G', 'GS']:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors='coerce')

    is_rp = (out.get('Pos') == 'RP') | (out.get('GS', 0).fillna(0) <= 3)
    rp_df = out[is_rp & (out.get('G', 0).fillna(0) >= 3)].copy()
    if rp_df.empty:
        # Fallback si pocos partidos: tomar todo out
        rp_df = out.copy()

    bullpen_rows = []
    teams = rp_df['Team'].dropna().unique()
    for tm in sorted(teams):
        tm_rps = rp_df[rp_df['Team'] == tm].copy()
        if tm_rps.empty:
            continue
        sort_by_cols = [c for c in ['SV', 'HLD', 'K%', 'SO'] if c in tm_rps.columns]
        if sort_by_cols:
            tm_rps = tm_rps.sort_values(by=sort_by_cols, ascending=[False]*len(sort_by_cols))
        for rank, (_, row) in enumerate(tm_rps.head(4).iterrows(), 1):
            sv = _safe_int(row.get('SV'))
            hld = _safe_int(row.get('HLD'))
            k_pct = row.get('K%', 0.0)
            stuff = row.get('Stuff+', 100)

            if rank == 1 and sv >= 3:
                role = '🔒 Cerrador (Closer)'
                status = 'Seguro' if sv >= 10 else 'Comité / En riesgo'
            elif sv >= 2 or hld >= 8:
                role = '🥈 Setup Primario (8va)'
                status = 'Next in line'
            elif hld >= 3 or (pd.notna(k_pct) and (k_pct > 0.28 or k_pct > 28)):
                role = '⚡ Setup / High Leverage'
                status = 'Sleeper de K / SV'
            else:
                role = '🛠️ Relevo Medio'
                status = 'Profundidad'

            bullpen_rows.append({
                'Team': tm,
                'Pitcher': row.get('Name', 'Pitcher'),
                'Role': role,
                'Status': status,
                'SV': sv,
                'HLD': hld,
                'ERA': row.get('ERA'),
                'WHIP': row.get('WHIP'),
                'K%': k_pct,
                'Stuff+': stuff,
            })
    return pd.DataFrame(bullpen_rows)
