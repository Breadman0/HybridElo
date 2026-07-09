import pandas as pd
import numpy as np
import sqlite3
from scipy.stats import spearmanr

def calculate_spearman_correlation():
    conn = sqlite3.connect('data/historic.db')
    query = """
        SELECT 
            pi.firstName || ' ' || pi.lastName AS player_name, 
            sr.mu, 
            sr.sigma_sq 
        FROM SKATER_RATINGS sr
        JOIN PLAYER_INFO pi ON sr.player_id = pi.player_id
    """
    model_df = pd.read_sql(query, conn)
    conn.close()

    model_df['sigma'] = np.sqrt(model_df['sigma_sq'])
    model_df['model_score'] = model_df['mu'] - (2 * model_df['sigma'])
    
    model_df = model_df.sort_values(by='model_score', ascending=False).reset_index(drop=True)
    model_df['model_rank'] = model_df.index + 1

    try:
        espn_df = pd.read_csv('data/espn_top_100.csv')
    except FileNotFoundError:
        print("Error: 'data/espn_top_100.csv' not found. Please verify the file path.")
        return

    espn_df = espn_df.rename(columns={
        'Player': 'player_name',
        'Rank': 'espn_rank'
    })

    model_df['match_name'] = model_df['player_name'].str.lower().str.strip()
    espn_df['match_name'] = espn_df['player_name'].str.lower().str.strip()

    merged_df = pd.merge(espn_df, model_df, on='match_name', how='inner')
    
    missing_players = len(espn_df) - len(merged_df)
    if missing_players > 0:
        print(f"⚠️ Notice: {missing_players} players from the ESPN list could not be matched due to name formatting discrepancies.")

    correlation, p_value = spearmanr(merged_df['espn_rank'], merged_df['model_rank'])

    print("\n" + "="*30 + " VALIDATION RESULTS " + "="*30)
    print(f"Players Matched in Intersection: {len(merged_df)} / {len(espn_df)}")
    print(f"Spearman's Rank Correlation (rho): {correlation:.4f}")
    print(f"Statistical Significance (p-value): {p_value:.3e}")
    print("="*80)

if __name__ == "__main__":
    calculate_spearman_correlation()