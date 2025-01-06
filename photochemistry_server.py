#Uncomment this if you use gunicorn
import eventlet
eventlet.monkey_patch(all=True, socket=True)


from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from rdkit import Chem
from rdkit.Chem import Descriptors
from pubchempy import get_compounds
import requests
from deep_translator import GoogleTranslator
import re
import firebase_admin
from firebase_admin import db
from time import strftime
from bs4 import BeautifulSoup
import wikipedia

app = Flask(__name__)
socketio = SocketIO(app,cors_allowed_origins='*' )
cred_obj = firebase_admin.credentials.Certificate('CENZURA')
default_app = firebase_admin.initialize_app(cred_obj, {'databaseURL':"CENZURA"})
ref = db.reference("/")
wikipedia.set_lang("cs")

@socketio.on('like')
def like():
    likes = ref.child("likeCount").get()
    ref.update({"likeCount": likes + 1})
    
@socketio.on('dislike')
def dislike():
    dislikes = ref.child("dislikeCount").get()
    ref.update({"dislikeCount": dislikes + 1})

def find_melting_point_value(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Melting Point":
            if "Information" in data:
                celsius_value = None
                first_value = None
                for info in data["Information"]:
                    if "Value" in info:
                        value = info["Value"]
                        for key, val in value.items():
                            if isinstance(val, list):
                                for item in val:
                                    if isinstance(item, dict) and "String" in item:
                                        if "°C" in item["String"]:
                                            return value
                                        if not celsius_value:
                                            celsius_value = value
                                    if first_value is None:
                                        first_value = value
                            if isinstance(val, list) and key.lower() == "number":
                                if first_value is None:
                                    first_value = value
                return celsius_value if celsius_value else first_value
        for key, value in data.items():
            result = find_melting_point_value(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_melting_point_value(item)
            if result is not None:
                return result
    return None

def find_canonical_smiles(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "SMILES":
            if "Information" in data:
                for info in data["Information"]:
                    if "Value" in info and "StringWithMarkup" in info["Value"]:
                        for item in info["Value"]["StringWithMarkup"]:
                            if "String" in item:
                                return item["String"]
        for key, value in data.items():
            result = find_canonical_smiles(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_canonical_smiles(item)
            if result is not None:
                return result
    return None

def find_boiling_point_value(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Boiling Point":
            if "Information" in data:
                celsius_value = None
                first_value = None
                for info in data["Information"]:
                    if "Value" in info:
                        value = info["Value"]
                        for key, val in value.items():
                            if isinstance(val, list):
                                for item in val:
                                    if isinstance(item, dict) and "String" in item:
                                        if "°C" in item["String"]:
                                            return value
                                        if not celsius_value:
                                            celsius_value = value
                                    if first_value is None:
                                        first_value = value
                            if isinstance(val, list) and key.lower() == "number":
                                if first_value is None:
                                    first_value = value
                return celsius_value if celsius_value else first_value
        for key, value in data.items():
            result = find_boiling_point_value(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_boiling_point_value(item)
            if result is not None:
                return result
    return None

def find_color_form(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Color/Form":
            if "Information" in data:
                for info in data["Information"]:
                    if "Value" in info:
                        value = info["Value"]
                        for key, val in value.items():
                            if isinstance(val, list):
                                for item in val:
                                    if isinstance(item, dict) and "String" in item:
                                        return item["String"]
                return None
        for key, value in data.items():
            result = find_color_form(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_color_form(item)
            if result is not None:
                return result
    return None

def find_odor(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Odor":
            if "Information" in data:
                for info in data["Information"]:
                    if "Value" in info:
                        value = info["Value"]
                        for key, val in value.items():
                            if isinstance(val, list):
                                for item in val:
                                    if isinstance(item, dict) and "String" in item:
                                        return item["String"]
                return None
        for key, value in data.items():
            result = find_odor(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_odor(item)
            if result is not None:
                return result
    return None

def find_taste(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Taste":
            if "Information" in data:
                for info in data["Information"]:
                    if "Value" in info:
                        value = info["Value"]
                        for key, val in value.items():
                            if isinstance(val, list):
                                for item in val:
                                    if isinstance(item, dict) and "String" in item:
                                        return item["String"]
                return None
        for key, value in data.items():
            result = find_taste(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_taste(item)
            if result is not None:
                return result
    return None

def find_uses(data):
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Uses":
            if "Information" in data:
                for info in data["Information"]:
                    if "Value" in info and "StringWithMarkup" in info["Value"]:
                        for markup in info["Value"]["StringWithMarkup"]:
                            if "String" in markup:
                                return markup["String"]
                return None
        for key, value in data.items():
            result = find_uses(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_uses(item)
            if result is not None:
                return result
    return None

def more_images_find(data):
    page_name = data
    img_urls = []
    img_descriptions = []
    result = []
    try:
        # Pokus o načtení přesného názvu stránky
        page = wikipedia.page(page_name)
    except wikipedia.exceptions.DisambiguationError as e:
        # Pokud je stránka nejednoznačná, vybere první možnost
        page_name = e.options[0]
        page = wikipedia.page(page_name)
        #print(f"Stránka byla nejednoznačná. Načítám stránku '{page_name}' místo toho.")
    except wikipedia.exceptions.PageError:
        # Pokud stránka neexistuje, vyhledá nejbližší shodu
        #print(f"Stránka '{page_name}' nebyla nalezena. Zkouším najít nejbližší shodu...")
        search_results = wikipedia.search(page_name)
        if search_results:
            page_name = search_results[0]
            page = wikipedia.page(page_name)
            #print(f"Načítám stránku '{page_name}' místo toho.")
        else:
            #print("Nenašel jsem žádnou vhodnou shodu.")
            return

    # Získání URL stránky
    url = page.url
    #print(f"Získávám obrázky a jejich popisy ze stránky: {url}")

    # Načtení stránky pomocí requests
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Najde všechny obrázky a vypíše URL s koncovkou .png nebo .jpg a jejich popisy
    images = soup.find_all('img')
    for index, img in enumerate(images):
        img_url = img['src']
        if img_url.startswith('//'):
            img_url = 'https:' + img_url

        if img_url.endswith('.png') or img_url.endswith('.jpg'):
            # Získání popisku z alt atributu nebo okolního textu
            alt_text = img.get('alt', 'Bez popisku')
            # Získání popisku z okolního textu, pokud alt atribut neexistuje
            parent_text = img.find_parent().get_text() if not alt_text else ''
            description = alt_text or parent_text.strip()
            if index != 0:
                if description != "":
                    if description != "Bez popisku":
                        if description != "Logo Wikimedia Commons":
                            if description != "Editovat na Wikidatech":
                                if description != "Upozornění":
                                    if description != "Tato stránka je zamčena pro neregistrované a nové uživatele":
                                        if description != "Pahýl":
                                            if description != "ikona":
                                                if not "GHS" in description:
                                                    img_urls.append(img_url)
                                                    img_descriptions.append(description)
            #print(f'Popis: {description}\n')
    result.append(img_urls)
    result.append(img_descriptions)
    s = strftime("%x--%X")
    print("["+s+"] More images on compound: "+ str(page_name))
    return result


@app.route('/', methods=['POST', 'GET'])
def start():
    return render_template('start.html')

@app.route('/ios', methods=['POST', 'GET'])
def ios():
    return render_template('ios.html')

@app.route('/privacy_policy', methods=['POST', 'GET'])
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/thanks', methods=['POST', 'GET'])
def thanks():
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()
    #print(user_agent)
    if "iphone" in user_agent:
        if "mobile" in user_agent:
            return render_template('thanks.html')
        else:
            return render_template('tablet_desktop_index.html')
    elif "android" in user_agent:
        if "mobile" in user_agent:
            return render_template('thanks.html')
        else:
            return render_template('tablet_desktop_index.html')
    else:
        return render_template('tablet_desktop_index.html')
    #return render_template('thanks.html')

@app.route('/scan', methods=['POST', 'GET'])
def index():
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()
    #print(user_agent)
    if "iphone" in user_agent:
        if "mobile" in user_agent:
            return render_template('mobile_index.html')
        else:
            return render_template('tablet_desktop_index.html')
    elif "android" in user_agent:
        if "mobile" in user_agent:
            return render_template('mobile_index.html')
        else:
            return render_template('tablet_desktop_index.html')
    else:
        return render_template('tablet_desktop_index.html')

@socketio.on('catch-frame')
def catch_frame(data):
    emit('response_back', data)  

@socketio.on('moreImages')
def more_images(data):
    result_more_images = more_images_find(data)
    emit('response_back_moreImages', {"img_url_list": result_more_images[0], "img_description_list": result_more_images[1]})

@socketio.on('moreImagesTP')
def more_imagesTP(data):
    result_more_images = more_images_find(data)
    emit('response_back_moreImagesTP', {"img_url_list": result_more_images[0], "img_description_list": result_more_images[1]})


@socketio.on('search')
def search(data_input):
    try:
        mol_name_en = GoogleTranslator(source='cs', target='en').translate(str(data_input))
        response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"+ mol_name_en.lower() +"/cids/JSON")
        data = response.json()
        response_data = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"+ str(data["IdentifierList"]["CID"][0]) +"/JSON")
        data_data = response_data.json()
        mol_name_cs = GoogleTranslator(source='en', target='cs').translate(str(data_data["Record"]["RecordTitle"]))
        s = strftime("%x--%X")
        print("["+s+"] Search response: "+ str(data_data["Record"]["RecordTitle"]))
        prevCount = ref.child("searchCount").get()
        ref.update({"searchCount": prevCount + 1})
        emit('response_back_search', {"mol_cid": data["IdentifierList"]["CID"][0], "mol_data": data_data, "mol_name_cs": mol_name_cs}) 
    except:
        emit('response_back_search', {"mol_cid": "neznámé", "mol_data": "neznámé", "mol_name_cs": "neznámé"})
@socketio.on('moreInfo')
def more_info(data_name):
    if data_name == "unknown":
        mol_weight = "neznámé"
        num_atoms = "neznámé"
        num_rings = "neznámé"
        boiling_point_value = "neznámé"
        melting_point_value = "neznámé"
        description = "neznámé"
    else:
        data = data_name
        melting_point_value = find_melting_point_value(data)
        if melting_point_value:
            try:
                melting_point_value = melting_point_value["StringWithMarkup"][0]["String"]
            except:
                pass
            try:
                melting_point_value = melting_point_value["Number"]
            except:
                pass
        else:
            melting_point_value = "neznámé"

        boiling_point_value = find_boiling_point_value(data)
        if boiling_point_value:
            try:
                boiling_point_value = boiling_point_value["StringWithMarkup"][0]["String"]
            except:
                pass
            try:
                boiling_point_value = boiling_point_value["Number"]
            except:
                pass
        else:
            boiling_point_value = "neznámé"

        color_form = find_color_form(data)
        odor = find_odor(data)
        taste = find_taste(data)

        if color_form:
            color_form_cs = GoogleTranslator(source='en', target='cs').translate(str(color_form)) + "; "
        else:
            color_form_cs = ""

        if odor:
            odor_cs = GoogleTranslator(source='en', target='cs').translate(str(odor)) + "; "
        else:
            odor_cs = ""

        if taste:
            taste_cs = GoogleTranslator(source='en', target='cs').translate(str(taste)) + "; "
        else:
            taste_cs = ""

        if color_form_cs == "" and odor_cs == "" and taste_cs == "":
            description = "neznámé"
        else:
            description = color_form_cs + odor_cs  + taste_cs

        isomeric_smiles = find_canonical_smiles(data)
        print(isomeric_smiles)
        m = Chem.MolFromSmiles(isomeric_smiles)
        # Get the molecular weight
        mol_weight = Descriptors.MolWt(m)
        rounded_mol_weight = round(mol_weight, 2)
        full_mol_weight = str(rounded_mol_weight) + " g/mol"

        # Get the number of atoms
        num_atoms = m.GetNumAtoms()

        # Get the number of rings
        num_rings = Descriptors.RingCount(m)
    s = strftime("%x--%X")
    print("["+s+"] More info response: " + data["Record"]["RecordTitle"])
    prevCount = ref.child("moreInfoCount").get()
    ref.update({"moreInfoCount": prevCount + 1})
    emit('response_back_mI', {"mol_weight": full_mol_weight, "num_atoms": num_atoms, "num_rings": num_rings, "mol_melting_point":melting_point_value, "mol_boiling_point":boiling_point_value, "mol_description":description.lower()})   

@socketio.on('moreInfoS')
def more_info_search(data_name):
    data = data_name
    melting_point_value = find_melting_point_value(data)
    if melting_point_value:
        try:
            melting_point_value = melting_point_value["StringWithMarkup"][0]["String"]
            melting_point_value = melting_point_value.replace(",", " ")
        except:
            pass
        try:
            melting_point_value = melting_point_value["Number"]
            melting_point_value = melting_point_value.replace(",", " ")
        except:
            pass
    else:
        melting_point_value = "neznámé"

    boiling_point_value = find_boiling_point_value(data)
    if boiling_point_value:
        try:
            boiling_point_value = boiling_point_value["StringWithMarkup"][0]["String"]
            boiling_point_value = boiling_point_value.replace(",", " ")
        except:
            pass
        try:
            boiling_point_value = boiling_point_value["Number"]
            boiling_point_value = boiling_point_value.replace(",", " ")
        except:
            pass
    else:
        boiling_point_value = "neznámé"

    color_form = find_color_form(data)
    odor = find_odor(data)
    taste = find_taste(data)

    if color_form:
        color_form_cs = GoogleTranslator(source='en', target='cs').translate(str(color_form)) + "; "
    else:
        color_form_cs = ""

    if odor:
        odor_cs = GoogleTranslator(source='en', target='cs').translate(str(odor)) + "; "
    else:
        odor_cs = ""

    if taste:
        taste_cs = GoogleTranslator(source='en', target='cs').translate(str(taste)) + "; "
    else:
        taste_cs = ""

    if color_form_cs == "" and odor_cs == "" and taste_cs == "":
        description = "neznámé"
    else:
        description = color_form_cs + odor_cs  + taste_cs

    isomeric_smiles = find_canonical_smiles(data)
    print(isomeric_smiles)
    m = Chem.MolFromSmiles(isomeric_smiles)
    mol_weight = Descriptors.MolWt(m)
    rounded_mol_weight = round(mol_weight, 2)
    full_mol_weight = str(rounded_mol_weight) + " g/mol"

    # Get the number of atoms
    num_atoms = m.GetNumAtoms()

    # Get the number of rings
    num_rings = Descriptors.RingCount(m)
    #os.remove('output'+str(compound.cid)+".png")
    mol_name_cs = GoogleTranslator(source='en', target='cs').translate(str(data["Record"]["RecordTitle"]))
    # emit the frame back
    s = strftime("%x--%X")
    print("["+s+"] More info response: " + data["Record"]["RecordTitle"])
    prevCount = ref.child("moreInfoCount").get()
    ref.update({"moreInfoCount": prevCount + 1})
    emit('response_back_mIS', {"mol_name_cs":mol_name_cs,"mol_weight": full_mol_weight, "num_atoms": num_atoms, "num_rings": num_rings, "mol_image":isomeric_smiles, "mol_melting_point":melting_point_value, "mol_boiling_point":boiling_point_value, "mol_description":description.lower()})

@socketio.on("imageMoreReaction")
def imageMoreReaction(data_list):
    #print(data_list)
    data_list.pop()
    #print(data_list)
    mol_image_list = []
    mol_name_list = []
    mol_data_list = []
    for i in range(len(data_list)):
        if (data_list[i] != "="):
            response_cid = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"+ str(data_list[i]) +"/cids/JSON")
            data_cid = response_cid.json()
            if not "IdentifierList" in data_cid:
                mol_name_cs = GoogleTranslator(source='en', target='cs').translate(data_list[i])
                
                mol_image_list.append("unknown")
                mol_data_list.append("unknown")
                mol_name_list.append(mol_name_cs)
                #print("unknown")
            else:
                response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"+ str(data_cid["IdentifierList"]["CID"][0]) +"/JSON")
                data = response.json()
                isomeric_smiles = find_canonical_smiles(data)
                print(isomeric_smiles)
                m = Chem.MolFromSmiles(isomeric_smiles)
                mol_image = isomeric_smiles
                mol_image_list.append(mol_image)

                mol_name_cs = GoogleTranslator(source='en', target='cs').translate(data_list[i])
                mol_name_list.append(mol_name_cs)

                mol_data_list.append(data)
        else:
            mol_image_list.append("=")
            mol_name_list.append("=")
            mol_data_list.append("=")
    s = strftime("%x--%X")
    print("["+s+"] More info response: " + str(mol_name_list))
    prevCount = ref.child("moreInfoCount").get()
    ref.update({"moreInfoCount": prevCount + 1})
    emit('response_back_iMR', {"mol_name_cs":mol_name_list, "mol_image":mol_image_list, "mol_data": mol_data_list})

def find_synonyms_section(data):
    """Rekurzivně hledá sekci s TOCHeading: Depositor-Supplied Synonyms."""
    if isinstance(data, dict):
        if data.get("TOCHeading") == "Depositor-Supplied Synonyms":
            if "Information" in data:
                synonyms = []
                for info in data["Information"]:
                    if "Value" in info:
                        value = info["Value"]
                        for entry in value.get("StringWithMarkup", []):
                            if isinstance(entry, dict) and "String" in entry:
                                synonyms.append(entry["String"])
                return synonyms[:5]  # Vrátí prvních 5 synonym
        for key, value in data.items():
            result = find_synonyms_section(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_synonyms_section(item)
            if result is not None:
                return result
    return None

def moreNamesGet(data_name):
    # Hledání sekce s TOCHeading: Depositor-Supplied Synonyms
    synonyms_string = ""
    synonyms = find_synonyms_section(data_name)

    # Výpis synonym
    if synonyms:
        for synonym in synonyms:
            synonyms_string += GoogleTranslator(source='en', target='cs').translate(synonym) + " / "
    
    else: synonyms_string = "neznámé   "

    return synonyms_string[:-3].lower()

def safetyGet(data_name):
    data = data_name

    try:
        chemical_safety = data["Record"]["Section"][1]["Information"][0]["Value"]["StringWithMarkup"][0]["Markup"]
    except:
        chemical_safety = []

    url_list = []
    image_list = []

    for i in range(len(chemical_safety)):
        url_list.append(chemical_safety[i]["URL"])
        image_list.append(GoogleTranslator(source='en', target='cs').translate(chemical_safety[i]["Extra"]))

    #print(url_list)
    #print(image_list)
    return url_list, image_list


@socketio.on('moreUsesTP')
def moreUsesTP(data_name):
    for compound in get_compounds(data_name, 'name'):
        compound_cid = str(compound.cid)
        response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/" + compound_cid + "/JSON")
        data = response.json()
        uses = find_uses(data)
        use_list = []

        if uses:
            uses_cs = GoogleTranslator(source='en', target='cs').translate(str(uses))
            uses_cs_cleaned = re.sub(r'\[[^\]]*\]', '', uses_cs)
            uses_cs_lower = uses_cs_cleaned.lower()
            uses_list = uses_cs_lower.split(";")
            #print(uses_list)

            for use in uses_list:
                if not use == " ":
                    #print(use.lstrip())
                    use_list.append(use.lstrip())
        else:
            use_list.append("neznámé")

        break
    emit('response_back_moreUsesTP', use_list)

@socketio.on('periodicTableMI')
def periodicTableMI(data_name, element_info):
    response_cid = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"+ str(data_name) +"/cids/JSON")
    data_cid = response_cid.json()
    response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"+ str(data_cid["IdentifierList"]["CID"][0]) +"/JSON")
    data = response.json()
    emit('response_back_periodicTableMI', {"data_element": data, "element_info": element_info})

@socketio.on('moreUsesS')
def moreUsesS(data_name):
    data = data_name
    uses = find_uses(data)
    use_list = []

    if uses:
        uses_cs = GoogleTranslator(source='en', target='cs').translate(str(uses))
        uses_cs_cleaned = re.sub(r'\[[^\]]*\]', '', uses_cs)
        uses_cs_lower = uses_cs_cleaned.lower()
        uses_list = uses_cs_lower.split(";")
        #print(uses_list)

        for use in uses_list:
            if not use == " ":
                #print(use.lstrip())
                use_list.append(use.lstrip())
    else:
        use_list.append("neznámé")

    emit('response_back_moreUsesS', use_list)

@socketio.on('moreSafetyS')
def moreSafetyS(data_name):
    safety_url, safety_name = safetyGet(data_name)
    emit('response_back_moreSafetyS', {"safety_url": safety_url, "safety_name": safety_name})

@socketio.on('moreSafetyMI')
def moreSafetyMI(data_name):
    safety_url, safety_name = safetyGet(data_name)
    emit('response_back_moreSafetyMI', {"safety_url": safety_url, "safety_name": safety_name})

@socketio.on('moreSafetyTP')
def moreSafetyTP(data_name):
    safety_url, safety_name = safetyGet(data_name)
    emit('response_back_moreSafetyTP', {"safety_url": safety_url, "safety_name": safety_name})

@socketio.on('moreNamesTP')
def moreNamesTP(data_name):
    emit('response_back_moreNamesTP', moreNamesGet(data_name))

@socketio.on('moreNamesMI')
def moreNamesTP(data_name):
    emit('response_back_moreNamesMI', moreNamesGet(data_name))

@socketio.on('moreNamesS')
def moreNamesS(data_name):
    emit('response_back_moreNamesS', moreNamesGet(data_name))

@socketio.on("reactionDesc")
def reactionDesc(data_name):
    try:
        api_key="CENZURA"
        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system",
                "content": [{
                "type": "text",
                "text": "Jsi analyzátor chemie. Uživatel ti pošle reakci, která bude zapsaná například takhle: ['kyselina fluorovodíková', 'hydroxid vápenatý', '=', 'fluorid vápenatý', 'voda']. Tvým úkolem je napsat postup vyčíslení dané reakce v bodech. Napiš jenom ty postupy. Nepiš nějakej začátek ani konec. Text nijak neformátuj akorát na konci každého řádku napiš \n a za každou dvojtečkou napiš taky \n a na začátku nového kroku taky napiš \n Každý krok očísluj."
                }]
            },
            {
            "role": "user",
            "content": [{
                "type": "text",
                "text": str(data_name)
                }]
            }
        ],
        "max_tokens": 800
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        #print(response.json())
        response_json = response.json()
        #print(response_json)
        response_txt = response_json["choices"][0]["message"]["content"]
        
        s = strftime("%x--%X")
        print("["+s+"] AI reaction description: " + str(data_name))
        prevCount = ref.child("reactionDescAI").get()
        ref.update({"reactionDescAI": prevCount + 1})
        emit('response_back_reactionDesc', response_txt)
    except:
        emit('response_back_reactionDesc', "Vyskytla se chyba při zpracování reakce. Zkuste to prosím znovu.")

@socketio.on("chemBotGPT")
def chemBotGPT(data_name):
    try:
        api_key="CENZURA"
        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system",
                "content": [{
                "type": "text",
                "text": "Jsi chemický chat bot. Uživatel ti napíše otázku, která se týká chemie a ty na ní odpovíš. Pokud ti napiše otázku, která se netýká chemie tak napiš 'Na tuto otázku nemohu odpovědět.'. Odpověď napiš tak aby byla ve formátu HTML včetně značek (p, div, atd ...). Použij i nějaké formátování (kurzívá, tučné písmo), pro lepší přehlednost."
                }]
            },
            {
            "role": "user",
            "content": [{
                "type": "text",
                "text": str(data_name)
                }]
            }
        ],
        "max_tokens": 800
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        #print(response.json())
        response_json = response.json()
        #print(response_json)
        response_txt = response_json["choices"][0]["message"]["content"]
        
        s = strftime("%x--%X")
        print("["+s+"] AI reaction description: " + str(data_name))
        prevCount = ref.child("reactionDescAI").get()
        ref.update({"reactionDescAI": prevCount + 1})
        print(response_txt)
        emit('response_back_chemBotGPT', response_txt)
    except:
        emit('response_back_chemBotGPT', "Vyskytla se chyba při zpracování reakce. Zkuste to prosím znovu.")

@socketio.on('moreInfoRTP')
def moreInfoRTP(data_name):
    try:
        api_key="CENZURA"
        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system",
                "content": [{
                "type": "text",
                "text": "You are chemical analyzer. When user enter some chemical compound the answer will be only 3 chemical reactions where the written compound exist. In the answer for example don't write H2SO4 write the name instead. Always write a name. Write it like this for example: sulfuric acid, sodium chloride, =, hydrogen chloride, sodium bisulfate, Reaction with hydroxide. At the end there MUST be the name of the reaction for example Neutralization or Reaction with hydroxide. If you dont know the name of the reaction just write Basic reaction. Don't forget to write the equal sign between two commas. There MUST be two commas between the equal sign. Between each reaction you MUST write '/'. Don't write commas before and after the '/'."
                }]
            },
            {
            "role": "user",
            "content": [{
                "type": "text",
                "text": data_name["Record"]["RecordTitle"]
                }]
            }
        ],
        "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        #print(response.json())
        response_json = response.json()
        response_txt = response_json["choices"][0]["message"]["content"]
        response_txt_list = response_txt.split("/ ")
        reaction_name_list = []
        reactions = []
        #print(response_txt)
        for i in range(len(response_txt_list)):
            response_txt_list_r = response_txt_list[i].split(", ")
            reactions.append(response_txt_list_r)
            reaction_name_cs = GoogleTranslator(source='en', target='cs').translate(response_txt_list_r[-1])
            reaction_name_list.append(reaction_name_cs)
        #print(reactions)
        #print(reaction_name_list)
        s = strftime("%x--%X")
        print("["+s+"] AI reaction response on photo: " + str(reaction_name_list))
        prevCount = ref.child("premiumReactionTP").get()
        ref.update({"premiumReactionTP": prevCount + 1})
        emit('response_back_mIRTP', {"reaction_type": reaction_name_list, "reaction1":reactions[0], "reaction2":reactions[1], "reaction3":reactions[2]})
    except:
        emit('response_back_mIRTP', {"reaction_type": "neznámé", "reaction1":"neznámé", "reaction2":"neznámé", "reaction3":"neznámé"})
        

@socketio.on('moreInfoRS')
def moreInfoRS(data_name):
    try:
        api_key="CENZURA"
        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system",
                "content": [{
                "type": "text",
                "text": "You are chemical analyzer. When user enter some chemical compound the answer will be only 3 chemical reactions where the written compound exist. In the answer for example don't write H2SO4 write the name instead. Always write a name. Write it like this for example: sulfuric acid, sodium chloride, =, hydrogen chloride, sodium bisulfate, Reaction with hydroxide. At the end there MUST be the name of the reaction for example Neutralization or Reaction with hydroxide. If you dont know the name of the reaction just write Basic reaction. Don't forget to write the equal sign between two commas. There MUST be two commas between the equal sign. Between each reaction you MUST write '/'. Don't write commas before and after the '/'."
                }]
            },
            {
            "role": "user",
            "content": [{
                "type": "text",
                "text": data_name["Record"]["RecordTitle"] 
                }]
            }
        ],
        "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        #print(response.json())
        response_json = response.json()
        response_txt = response_json["choices"][0]["message"]["content"]
        response_txt_list = response_txt.split("/ ")
        reaction_name_list = []
        reactions = []
        #print(response_txt)
        for i in range(len(response_txt_list)):
            response_txt_list_r = response_txt_list[i].split(", ")
            reactions.append(response_txt_list_r)
            reaction_name_cs = GoogleTranslator(source='en', target='cs').translate(response_txt_list_r[-1])
            reaction_name_list.append(reaction_name_cs)
        #print(reactions)
        #print(reaction_name_list)
        s = strftime("%x--%X")
        print("["+s+"] AI reaction response on search: " + str(reaction_name_list))
        prevCount = ref.child("premiumReactionS").get()
        ref.update({"premiumReactionS": prevCount + 1})

        emit('response_back_mIRS', {"reaction_type": reaction_name_list, "reaction1":reactions[0], "reaction2":reactions[1], "reaction3":reactions[2]})
    except:
        emit('response_back_mIRS', {"reaction_type": "neznámé", "reaction1":"neznámé", "reaction2":"neznámé", "reaction3":"neznámé"})
@socketio.on('image')
def image(data_image):

    api_key="CENZURA"
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }

    payload = {
    "model": "gpt-4o",
    "messages": [
        {"role": "system",
            "content": [{
            "type": "text",
            "text": 'You are chemical image analyzer. If on image is only some chemical compound write "compound, compound name" the name of the compound and nothing more. (for example: compound, benzene) If on the picture is arrow or sum of compound it means it is chemical reaction. Then the answer will be "reaction, product names". The other compound can be under or up of the arrow. These compounds are reagents, they can help you what will be the products. Write the name of starting material from image, and also products name like for example Sulfuric acid.  (for example: reaction, benzene, ammonia, arrow, oxane, brom). The "arrow" that after the arrow will be name of products.  The "arrow" must be in every reaction. If on the picture is full chemical reaction it means it must be solved. Then the answer will be "solving reaction, count of stoichiometric coefficient". Count of stoichiometric coefficient means that you will write count of every starting material and count of every product. Use always a name not the structure. (for example: solving reaction, 6/carbon dioxide, 12/water, arrow, 1/glucose, 6/oxygen, 6/water) The "arrow" that after the arrow will be name of products. The "arrow" must be in every solving reaction. If there isnt a chemical think that you can analyze the answer will be: notchem. If on the picture is more than one chemical problem to solve the answer will be: toomuch.'
            }]
        },
        {
        "role": "user",
        "content": [{
            "type": "image_url",
            "image_url": {
                "url": data_image
            }}]
        }
    ],
    "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    #print(response.json())
    response_json = response.json()
    if "error" in response_json:
        error_name_cs = GoogleTranslator(source='en', target='cs').translate(response_json["error"]["message"])
        s = strftime("%x--%X")
        print("["+s+"] Error AI: "+ response_json["error"]["message"])
        prevCount = ref.child("errorCount").get()
        ref.update({"errorCount": prevCount + 1})
        emit("response_back", {"error_name":error_name_cs, "type":"error"})
    else:
        response_txt = response_json["choices"][0]["message"]["content"]
        response_txt_list = response_txt.split(", ")
        #print(response_txt_list)

        if (response_txt_list[0]=="compound"):
            compound_name = response_txt_list[1]
            #print(compound_name)
            
            response_cid = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"+ str(compound_name) +"/cids/JSON")
            data_cid = response_cid.json()

            if not "IdentifierList" in data_cid:
                mol_name_cs = GoogleTranslator(source='en', target='cs').translate(compound_name)
                mol_image = "unknown"
                mol_weight = "..."
                num_atoms = "..."
                num_rings = "..."
                boiling_point_value = "neznámé"
                melting_point_value = "neznámé"
                description = "neznámé"

            else:
                response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"+ str(data_cid["IdentifierList"]["CID"][0]) +"/JSON")
                data = response.json()
                melting_point_value = find_melting_point_value(data)
                if melting_point_value:
                    try:
                        melting_point_value = melting_point_value["StringWithMarkup"][0]["String"]
                        melting_point_value = melting_point_value.replace(",", " ")
                    except:
                        pass
                    try:
                        melting_point_value = melting_point_value["Number"]
                        melting_point_value = melting_point_value.replace(",", " ")
                    except:
                        pass
                else:
                    melting_point_value = "neznámé"

                boiling_point_value = find_boiling_point_value(data)
                if boiling_point_value:
                    try:
                        boiling_point_value = boiling_point_value["StringWithMarkup"][0]["String"]
                        boiling_point_value = boiling_point_value.replace(",", " ")
                    except:
                        pass
                    try:
                        boiling_point_value = boiling_point_value["Number"]
                        boiling_point_value = boiling_point_value.replace(",", " ")
                    except:
                        pass
                else:
                    boiling_point_value = "neznámé"

                color_form = find_color_form(data)
                odor = find_odor(data)
                taste = find_taste(data)

                if color_form:
                    color_form_cs = GoogleTranslator(source='en', target='cs').translate(str(color_form)) + "; "
                else:
                    color_form_cs = ""

                if odor:
                    odor_cs = GoogleTranslator(source='en', target='cs').translate(str(odor)) + "; "
                else:
                    odor_cs = ""

                if taste:
                    taste_cs = GoogleTranslator(source='en', target='cs').translate(str(taste)) + "; "
                else:
                    taste_cs = ""

                if color_form_cs == "" and odor_cs == "" and taste_cs == "":
                    description = "neznámé"
                else:
                    description = color_form_cs + odor_cs  + taste_cs

                isomeric_smiles = find_canonical_smiles(data)
                print(isomeric_smiles)
                m = Chem.MolFromSmiles(isomeric_smiles)
                
                mol_weight = Descriptors.MolWt(m)
                rounded_mol_weight = round(mol_weight, 2)
                full_mol_weight = str(rounded_mol_weight) + " g/mol"

                # Get the number of atoms
                num_atoms = m.GetNumAtoms()

                # Get the number of rings
                num_rings = Descriptors.RingCount(m)
                mol_name_cs = GoogleTranslator(source='en', target='cs').translate(compound_name)
                mol_image = isomeric_smiles
                
                # emit the frame back
            s = strftime("%x--%X")
            print("["+s+"] Compound response of AI detection: "+ compound_name)
            prevCount = ref.child("compoundAI").get()
            ref.update({"compoundAI": prevCount + 1})
            emit('response_back', {"mol_name_cs":mol_name_cs, "mol_weight": full_mol_weight, "num_atoms": num_atoms, "num_rings": num_rings, "mol_image":mol_image, "mol_name_en": compound_name ,"type":"compound", "mol_melting_point":melting_point_value, "mol_boiling_point":boiling_point_value, "mol_description":description.lower(), "mol_data": data})
        if (response_txt_list[0]=="reaction"):
            reactionCompoundImageList = []
            reactionCompoundNameList = []
            reactionCompoundDataList = []
            for i in range(len(response_txt_list)):

                if i == 0: pass
                    #print(response_txt_list[i])

                elif response_txt_list[i] == "arrow":
                    #print(" => ")
                    reactionCompoundImageList.append("=")
                    reactionCompoundNameList.append("=")
                    reactionCompoundDataList.append("=")
                else:
                    response_cid = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"+ str(response_txt_list[i]) +"/cids/JSON")
                    data_cid = response_cid.json()

                    if not "IdentifierList" in data_cid:
                        mol_name_cs = GoogleTranslator(source='en', target='cs').translate(response_txt_list[i])
                        reactionCompoundImageList.append("unknown")
                        reactionCompoundDataList.append("unknown")
                        reactionCompoundNameList.append(mol_name_cs)
                    else:   
                        response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"+ str(data_cid["IdentifierList"]["CID"][0]) +"/JSON")
                        data = response.json()
                        reactionCompoundDataList.append(data)
                        isomeric_smiles = find_canonical_smiles(data)
                        print(isomeric_smiles)
                        m = Chem.MolFromSmiles(isomeric_smiles)
                        mol_image = isomeric_smiles
                        mol_name_cs = GoogleTranslator(source='en', target='cs').translate(response_txt_list[i])
                        reactionCompoundImageList.append(mol_image)
                        reactionCompoundNameList.append(mol_name_cs)
                      
            #print(reactionCompoundImageList)
            #print(reactionCompoundNameList)
            s = strftime("%x--%X")
            print("["+s+"] Reaction response of AI detection: "+ str(reactionCompoundNameList))
            prevCount = ref.child("reactionAI").get()
            ref.update({"reactionAI": prevCount + 1})
            emit('response_back', { "mol_name_cs":reactionCompoundNameList, "mol_image":reactionCompoundImageList, "type":"reaction", "mol_data": reactionCompoundDataList})
        if (response_txt_list[0]=="solving reaction"):
            reactionCompoundImageList = []
            reactionCompoundNameList = []
            reactionCompoundCountList = []
            reactionCompoundDataList = []
            for i in range(len(response_txt_list)):
                if i == 0: pass
                    #print(response_txt_list[i])
                elif response_txt_list[i] == "arrow":
                    #print(" => ")
                    reactionCompoundImageList.append("=")
                    reactionCompoundNameList.append("=")
                    reactionCompoundCountList.append("=")
                    reactionCompoundDataList.append("=")
                else:
                    solving_reaction_list = response_txt_list[i].split("/")
                    #print(solving_reaction_list)
                    reactionCompoundCountList.append(solving_reaction_list[0])
                    response_cid = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"+ str(solving_reaction_list[1]) +"/cids/JSON")
                    data_cid = response_cid.json()

                    if not "IdentifierList" in data_cid:
                        mol_name_cs = GoogleTranslator(source='en', target='cs').translate(solving_reaction_list[1])
                        reactionCompoundImageList.append("unknown")
                        reactionCompoundDataList.append("unknown")
                        reactionCompoundNameList.append(mol_name_cs)
                    else:
                        response = requests.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"+ str(data_cid["IdentifierList"]["CID"][0]) +"/JSON")
                        data = response.json()
                        reactionCompoundDataList.append(data)
                        isomeric_smiles = find_canonical_smiles(data)
                        print(isomeric_smiles)
                        m = Chem.MolFromSmiles(isomeric_smiles)
                        mol_image = isomeric_smiles
                        mol_name_cs = GoogleTranslator(source='en', target='cs').translate(solving_reaction_list[1])
                        reactionCompoundImageList.append(mol_image)
                        reactionCompoundNameList.append(mol_name_cs)
            #print(reactionCompoundCountList)
            #print(reactionCompoundNameList)
            #print(reactionCompoundImageList)
            s = strftime("%x--%X")
            print("["+s+"] Solving reaction response of AI detection: "+ str(reactionCompoundNameList))
            prevCount = ref.child("solvingReactionAI").get()
            ref.update({"solvingReactionAI": prevCount + 1})
            emit('response_back', { "mol_name_cs":reactionCompoundNameList, "mol_image":reactionCompoundImageList, "mol_count":reactionCompoundCountList, "type":"solving reaction", "mol_data": reactionCompoundDataList})

        if(response_txt_list[0]=="notchem"):
            s = strftime("%x--%X")
            print("["+s+"] AI detection response: No chemical compound detected.")
            prevCount = ref.child("notChemError").get()
            ref.update({"notChemError": prevCount + 1})
            emit("response_back", {"error_name":"Na obrázku není nic spojeného s chemií.", "type":"error"})

        if(response_txt_list[0]=="toomuch"):
            s = strftime("%x--%X")
            print("["+s+"] AI detection response: Too much chemical compounds detected.")
            prevCount = ref.child("tooMuchError").get()
            ref.update({"tooMuchError": prevCount + 1})
            emit("response_back", {"error_name":"Na obrázku je víc než jeden chemický problém. Při ořezu ořízněte jenom jeden.", "type":"error"})




#Comment this if you use gunicorn
#if __name__ == '__main__':
#    app.config['TEMPLATES_AUTO_RELOAD'] = True
#    socketio.run(app,port=8080,ssl_context=('certificate.crt', 'privatekey.key'),host="0.0.0.0")
   


