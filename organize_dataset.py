import os
import shutil

# Diccionario mapeando el ID (como string '001', '002') al nombre de la clase
# Formateamos los nombres reemplazando espacios por guiones bajos y en minúsculas para prolijidad
sign_mapping = {
    '001': 'opaque', '002': 'red', '003': 'green', '004': 'yellow', '005': 'bright',
    '006': 'light-blue', '007': 'colors', '008': 'pink', '009': 'women', '010': 'enemy',
    '011': 'son', '012': 'man', '013': 'away', '014': 'drawer', '015': 'born',
    '016': 'learn', '017': 'call', '018': 'skimmer', '019': 'bitter', '020': 'sweet_milk',
    '021': 'milk', '022': 'water', '023': 'food', '024': 'argentina', '025': 'uruguay',
    '026': 'country', '027': 'last_name', '028': 'where', '029': 'mock', '030': 'birthday',
    '031': 'breakfast', '032': 'photo', '033': 'hungry', '034': 'map', '035': 'coin',
    '036': 'music', '037': 'ship', '038': 'none', '039': 'name', '040': 'patience',
    '041': 'perfume', '042': 'deaf', '043': 'trap', '044': 'rice', '045': 'barbecue',
    '046': 'candy', '047': 'chewing-gum', '048': 'spaghetti', '049': 'yogurt', '050': 'accept',
    '051': 'thanks', '052': 'shut_down', '053': 'appear', '054': 'to_land', '055': 'catch',
    '056': 'help', '057': 'dance', '058': 'bathe', '059': 'buy', '060': 'copy',
    '061': 'run', '062': 'realize', '063': 'give', '064': 'find'
}

def organize_dataset(raw_dir):
    organized_dir = os.path.join(os.path.dirname(raw_dir), 'raw_organized')
    os.makedirs(organized_dir, exist_ok=True)
    
    # Asegurarnos de que las carpetas de las 64 clases existan
    for sign_name in sign_mapping.values():
        os.makedirs(os.path.join(organized_dir, sign_name), exist_ok=True)
        
    videos = [f for f in os.listdir(raw_dir) if f.endswith('.mp4')]
    moved = 0
    
    print(f"Encontrados {len(videos)} videos en {raw_dir}")
    
    for video in videos:
        # El formato es CLASE_SUJETO_REPETICION.mp4 (ej: 001_001_001.mp4)
        parts = video.split('_')
        if len(parts) >= 3:
            class_id = parts[0]
            if class_id in sign_mapping:
                class_name = sign_mapping[class_id]
                src = os.path.join(raw_dir, video)
                dst = os.path.join(organized_dir, class_name, video)
                shutil.move(src, dst)
                moved += 1
            else:
                print(f"Clase ID {class_id} no encontrada en el diccionario para {video}")
                
    print(f"Organización completa: {moved} videos movidos a {organized_dir}")

if __name__ == '__main__':
    raw_directory = 'c:/Nexora/data/raw'
    organize_dataset(raw_directory)
