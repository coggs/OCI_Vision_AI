from pdf2image import convert_from_path
import requests
import oci
import ujson as json
import random
import base64
import sys
import os
import oracledb

config = oci.config.from_file()
ai_vision_client = oci.ai_vision.AIServiceVisionClient(config)

url = "https://ns.objectstorage.ap-sydney-1.oci.customer-oci.com/n/ns/b/bucket/o/"
compartment_id = "ocid1.compartment.oc1..aaxsp2np7a"
namespace= ""
bucket = ""

# DB Set up
connection=oracledb.connect(
     config_dir="/home/opc/wallet/walletname",
     user="dbuser",
     password="dbpasswd",
     dsn="atp_low",
     wallet_location="/home/opc/wallet/walletname",
     wallet_password="walletpw"
)

call_update_sql = """UPDATE atable SET JSON_DATA = :json_data WHERE FILENAME = :filename"""

def get_base64_encoded_image(image_path): # encode image to Base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Fetch Document List
r = requests.get(url)

data = r.json()
# print(data)

newlist = []
for name in data['objects']:
    newlist.append((name['name']))

# print(newlist)
length = len(newlist)
newurl = []

# Loop Through all documents in Folder
with connection.cursor() as cursor:

    for p in range(52,length):
        newurl = url + newlist[p]

        pdffile = newlist[p]

        config = oci.config.from_file()
        object_storage_client = oci.object_storage.ObjectStorageClient(config)

        get_obj = object_storage_client.get_object(namespace, bucket, pdffile)
        with open('./'+ pdffile,'wb') as f:
            for chunk in get_obj.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)
            print(f'{p} - Downloaded "{pdffile}" from bucket "{bucket}"')

        # Load a document
        try:
            images = convert_from_path("./" + pdffile)
        except:
                print("Doc Failed.. moving on")
                continue
        # Create JSON Object to store PDF Data
        pdfdoc = {
            "document_name": "PDFDOC", 
            "pages":  []
            }

        pdfdoc["document_name"] = newlist[p]

        for i in range(len(images)):
            # Save pages as images in the pdf
            imagePath = "./images/page" + str(i) + '.jpg'
            images[i].save(imagePath, 'JPEG')
            
            pdfpage = get_base64_encoded_image(imagePath)

            random_number = random.randint(0, 500000)
            # Send Image to AI Service
            analyse_image = ai_vision_client.analyze_image(
            analyze_image_details = oci.ai_vision.models.AnalyzeImageDetails(
                features=[
                    oci.ai_vision.models.ImageObjectDetectionFeature(
                        max_results=10,feature_type="TEXT_DETECTION")],
                image=oci.ai_vision.models.InlineImageDetails(
                    source="INLINE",
                    data = pdfpage),
                compartment_id=compartment_id))
            
            jdata = json.loads(str(analyse_image.data))

            # First, we will check the consistency of the JSON object.
            try:
                jdata['image_text']
            except KeyError as e:
                print('Error in JSON data structure. Exiting...')
                sys.exit(-100)
            
            # list of responses
            labels = jdata['image_text']["lines"]

            pt = ""
            for item in labels: 
                pt = pt + item["text"] + " "

            page = {
                "page": i+1,
                "text_content": pt
            }
        
            pdfdoc['pages'].append(page)

        #print(json.dumps(pdfdoc))

            os.remove("./images/page" + str(i) + ".jpg")

        os.remove("./" + pdffile)

        cursor.execute(call_update_sql, [json.dumps(pdfdoc), pdffile])

        connection.commit()
