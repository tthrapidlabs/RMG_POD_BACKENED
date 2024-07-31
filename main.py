from openai import AzureOpenAI
import ast
import base64
from mimetypes import guess_type
from flask import Flask, render_template, request, send_file , json , jsonify
from PIL import Image, ImageDraw, ImageFont  
import PyPDF2      
import openai  
import re  
import os 
import base64
from mimetypes import guess_type

from flask import Response  
from flask_cors import CORS 
import shutil
import time

app = Flask(__name__) 
UPLOAD_FOLDER = 'images'  # Change this to your folder name
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 
CORS(app)
      

def empty_upload_folder():
    folder_path = app.config['UPLOAD_FOLDER']
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path)

@app.route('/upload', methods=['POST'])
def upload_file():

    # x = {'valid': True, 'reason': []}
    # y = {'valid': False, 'reason': ['door is not visible', 'picture is blurry', 'no proof that it"s delivered to customer']}

    # return jsonify({'status' : 'SUCCESS','message': 'Files uploaded successfully', 'data' : x})

 
    if 'file' not in request.files:
        print('No files part')
        return jsonify({'error': 'No files part'})

    empty_upload_folder()

    file = request.files.get('file')

    if file.filename == '':
        print('One of the selected files has no name')
        return jsonify({'error': 'One of the selected files has no name'})
 
    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filename)

    def local_image_to_data_url(image_path):
    
        mime_type, _ = guess_type(image_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'  

        
        with open(image_path, "rb") as image_file:
            base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

        
        return f"data:{mime_type};base64,{base64_encoded_data}"

    
    filename = os.listdir(UPLOAD_FOLDER)
    filename1 = filename[0]
    image_path = "images/"+ filename1
    data_url = local_image_to_data_url(image_path)

    guidelines = """
    Parcel should be visible.
    Door picture(fully/partially visible) or address picture with customer holding the parcel with visible parcel (Proof that parcel is handed over to customer). Door can be either open/close.
    If customer taking the parcel than the Customer hand should visible with parcel details.
    If the item's can fit through letterbox, place parcel item in half and take a picture of it.
    no personal information should not be visible in the picture and dont photograph the customer face(if it shows the customer body without face than it is a valid picture)
    even if the customer face is partially visible, it should not recognize the person identity. than that picture is valid and acceptable.
    """
    accepted = """
        1. Parcel is visible
        2. door is visible(fully/partillay)
        3. If the item's can fit through letterbox, place parcel item in half and take a picture of it.
        4. customer is visible (customer face should not be visible). even if the customer face is partially visible, it should not recognize the person identity. than that picture is valid and acceptable.
    """
    rejected = '''
        1. Door is not visible in the picture
        2. Picture is blurry
        3. only parcel is visible in the picture.
    '''
    resp = {
        "valid" : False,
        "reason" : ['door is not visible', 'parcel is blurry', 'no proof that its delivered to customer']
        }
    dummy_response = {
        "valid" : False,
        "reason" : ["Please Take another picture and upload"]
    }
    try:
        deployment_name = 'rmgvision'
        api_version = '2023-12-01-preview'
        api_base = "https://visionrmgusecase.openai.azure.com/"  
        api_key = "efc2fe2c21a04557a3508b19c054e8eb"

        client = AzureOpenAI(
            api_key=api_key,  
            api_version=api_version,
            base_url=f"{api_base}openai/deployments/{deployment_name}/extensions",
        )

        # start time
        start_time = time.time()

        response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            { "role": "system", "content": f"This is a Post on delivery service where the postman will take a picture of the parcel on delivery for proof purpose.There are some guidelines for acceptance of the picture. You have to check the picture carefully and give response as Valid or Invalid based on the guidelines.The guidelines for a valid photo are {guidelines}. {rejected} These are some points for a picture to be invalid/rejected.{accepted} are the points for the accepted pictures.If the door is not showing even partially than that picture is a invalid picture.the door should visible clearly.one should recognize that its a door than only that picture is valid." },
                { "role": "user", "content": [  
                    { 
                        "type": "text", 
                        "text": f"Based on the given guidelines verify the image is valid or not.give the output in this {resp} format. where it should have valid and reason. the valid should be True/False and for reason give me a list of reasons why the picture is invalid for valid picture keep the list as empty . if the input image is valid than give 'valid' as True or else 'valid' as False and also provide the reason as list. For valid picture no need for resasons so just give an empty list for that one and for invalid picture give me all the reasons why the picture is invalid as a list.Give reasons in short sentences.Dont hallucinate anything.only take consideration of given guidelines for validation of the image.only give output dont add anything to it.check the uploaded picture carefully and give output. if the picture is not related to parcel delivery than give repsonse as the uploaded picture is invalid and give reasons why it is invalid.for example if the user uploads the picture of flower or car or anything other than parcel delivering than you have give valid as False and reason as please upload a valid picture."
                    },
                { 
                    "type": "image_url",
                    "image_url": {
                    "url":data_url,
                    "detail":"high"
                    }
                }
            ] } 
        ],
        extra_body={
                "dataSources": [
                    {
                        "type": "AzureComputerVision",
                        "parameters": {
                            "endpoint": "https://visioncheck123.cognitiveservices.azure.com/",
                            "key": "e69c5ac2a756493d9502b640865fdd4e"
                        }
                    }],
                "enhancements": {
                    "ocr": {
                        "enabled": True
                    },
                    "grounding": {
                        "enabled": True
                    }
                }
            },

        temperature=0.1,          
        max_tokens=2000,          
        top_p=1,          
        frequency_penalty=0,          
        presence_penalty=0,
            )
        output = response.choices[0].message.content
        print(output)

        out2 = ast.literal_eval(output) 
        print(out2)
        # print(type(ast.literal_eval(output)))
        # print(out2["valid"])

        # calculate and display the end time
        execution_time = time.time() - start_time
        print(f"Execution time: {execution_time:.2f} seconds")



        return jsonify({'status' : 'SUCCESS','message': 'Files uploaded successfully', 'data' : out2})
    
    except Exception as e:
        print(e)

        return jsonify({'status' : 'SUCCESS','message': 'Files uploaded successfully', 'data' : dummy_response})



if __name__ == '__main__':
    app.run(debug=True, port=8000) 

