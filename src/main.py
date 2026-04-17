import argparse
import os
import sys
import pandas as pd

from dataScraping.DataSaver import run_snowball_to_csv
from dataScraping.GameMetadanaScraper import GameMetadataScraper

def extract_unique_games(edges_path, output_path):
    if not os.path.exists(edges_path):
        print(f"Błąd: Plik {edges_path} nie istnieje.")
        return

    df = pd.read_csv(edges_path)
    game_edges = df[df['type'] == 'game']
    
    unique_ids = game_edges['target'].str.replace('App_', '').unique()
    
    df_unique = pd.DataFrame(unique_ids, columns=['app_id'])
    df_unique.to_csv(output_path, index=False)
    print(f"Wyodrębniono {len(unique_ids)} unikalnych gier do {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Steam Network Analysis Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)


    parser_snowball = subparsers.add_parser("snowball")
    parser_snowball.add_argument("--seed", required=True, help="Startowy SteamID64")
    parser_snowball.add_argument("--limit", type=int, default=1000, help="Limit rekordów")

    parser_extract = subparsers.add_parser("extract")
    parser_extract.add_argument("--input", default="data/edges.csv")
    parser_extract.add_argument("--output", default="data/unique_games.csv")

    parser_metadata = subparsers.add_parser("metadata")
    parser_metadata.add_argument("--input", required=True, help="Plik z listą ID gier")
    parser_metadata.add_argument("--output", default="data/game_info.csv")

    args = parser.parse_args()

    if args.command == "snowball":
        run_snowball_to_csv(args.seed, args.limit)
    
    elif args.command == "extract":
        extract_unique_games(args.input, args.output)
    
    elif args.command == "metadata":
        scraper = GameMetadataScraper(args.output)
        
        df_apps = pd.read_csv(args.input)
        ids_to_fetch = df_apps['app_id'].tolist()
        
        scraper.run(ids_to_fetch)

if __name__ == "__main__":
    main()