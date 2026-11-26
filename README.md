# Parking Intelligent

Application desktop Tkinter locale pour le pointage des véhicules dans un parking tunisien.
La détection et la reconnaissance fonctionnent localement, sans API d'IA cloud.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Lancement

```powershell
python -m src.vision.download_models
python -m src.main
```

La première commande télécharge YOLOv4-tiny dans `models/`. EasyOCR installe
ses poids locaux au premier usage (une connexion est requise uniquement pour
récupérer les poids manquants). Une fois les modèles disponibles, l'inférence
est effectuée sur la machine. Sans caméra, l'application reste utilisable et
affiche un message d'indisponibilité pour chaque source.

## Mode Test

Placez une ou plusieurs vidéos locales dans `test-video/`, puis activez
**Mode Test** dans l'en-tête. Les formats acceptés sont configurés dans
`src/config.py`. Une vidéo est sélectionnée pour chaque caméra; s'il y a
plusieurs fichiers, utilisez les listes **Vidéo Entrée** et **Vidéo Sortie**.
Les vidéos bouclent et peuvent être mises en pause ou reprises depuis les
panneaux caméra.

Le mode test est isolé : ses pointages sont stockés dans
`data/parking_test.db` et ses captures dans `data/captures_test/`. Le bouton
**Réinitialiser les données de test** supprime ces données après confirmation.
Le mode normal continue d'utiliser `data/parking.db` et `data/captures/`.

Chaque véhicule suivi produit automatiquement deux images, dans les sous-dossiers
`{entry|exit}/{YYYY-MM-DD}/` : une découpe du véhicule et une découpe de plaque.
Les noms suivent `{timestamp}_{plate_key}_car.jpg` et
`{timestamp}_{plate_key}_plate.jpg`; la clé `unknown` est utilisée si la plaque
n'a pas encore été reconnue.

## Limites mesurées

La vidéo de démonstration fournie est une scène de circulation routière, pas un
jeu d'images de plaques tunisiennes. Sur les trois images de `tests/data/`,
YOLOv4-tiny a détecté respectivement 5, 8 et 7 véhicules. Les plaques y sont
trop petites pour être lues : ces images ne mesurent donc pas la précision de
l'OCR.

Sur des plaques tunisiennes synthétiques (texte `NNN تونس NNNN` rendu avec de
vraies polices), l'étape OCR lit correctement **2 plaques sur 3** avec EasyOCR,
contre 0 sur 3 avant la correction du parseur. Le troisième cas est un chiffre
isolé très fin que le détecteur de texte d'EasyOCR ne voit pas ; l'opérateur
confirme alors la lecture. Cette mesure porte sur l'OCR d'images synthétiques,
pas sur des photos réelles, et ne constitue pas une garantie de précision.

## Corrections OCR

La lecture échouait parce qu'EasyOCR lit de droite à gauche : le groupe de
chiffres de droite se collait au mot arabe (ex. `"4567 سنوت"`) et `تونس` était
souvent mal lu. Le parseur reconstruit désormais la plaque à partir de ses deux
groupes de chiffres (1-3 puis 1-4), tolère une bande mal lue ou inversée, et
rejette toujours le texte libre. Voir `src/vision/ocr_reader.py`.

## Test

```powershell
pytest -q
```

## Configuration caméra

Les sources peuvent être configurées par variables d'environnement :

```powershell
$env:SPMS_ENTRY_CAMERA="0"
$env:SPMS_EXIT_CAMERA="1"
$env:SPMS_ENTRY_SOURCE=""
$env:SPMS_EXIT_SOURCE=""
python -m src.main
```

La base SQLite est créée automatiquement dans `data/parking.db`. Les tests
unitaires et les contrôles d'images sont lancés avec `pytest -q`.

## Générer un exécutable Windows

Installez les dépendances de l'application et l'outil de compilation, puis
construisez l'exécutable unique :

```powershell
pip install -r requirements.txt -r requirements-build.txt
python -m PyInstaller --clean --noconfirm parking_intelligent.spec
```

Le résultat est `dist/ParkingIntelligent.exe`. Les modèles locaux et la vidéo
de démonstration sont intégrés dans ce fichier; la compilation produit donc un
exécutable volumineux et le premier démarrage peut prendre un moment. Les bases
et captures restent dans `data/` à côté de l'exécutable et ne sont pas incluses.
Pour choisir d'autres vidéos, placez-les dans `test-video/` à côté du fichier
EXE; sinon, le clip de démonstration intégré est utilisé.
