import csv
import os

def prune_edges_for_gephi(input_file, output_file, min_cosine=0.08, min_shared=10):
    print(f"Rozpoczynam filtrowanie pliku: {input_file}")
    
    saved = 0
    dropped = 0
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', newline='', encoding='utf-8') as f_out:
         
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        header = next(reader, None)
        if header:
            writer.writerow(header)
            
        try:
            cosine_idx = header.index('cosine')
            shared_idx = header.index('shared_players')
        except ValueError:
            print("Blad naglowkow.")
            return
            
        for row in reader:
            try:
                cosine_val = float(row[cosine_idx])
                shared_val = int(row[shared_idx])
                
                if cosine_val >= min_cosine and shared_val >= min_shared:
                    writer.writerow(row)
                    saved += 1
                else:
                    dropped += 1
            except (ValueError, IndexError):
                dropped += 1
                
    print(f"Gotowe! Zapisano: {saved} krawedzi.")
    print(f"Odrzucono (szum): {dropped} krawedzi.")

if __name__ == "__main__":
    INPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'game_game_rich_projection.csv')
    OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data','edges_gephi_lighter.csv')
    
    prune_edges_for_gephi(INPUT_FILE, OUTPUT_FILE)