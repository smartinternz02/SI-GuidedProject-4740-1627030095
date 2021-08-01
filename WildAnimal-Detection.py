import cv2
import numpy as np
import datetime
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import service_pb2_grpc
import datetime
import ibm_boto3
from ibm_botocore.client import Config, ClientError
from ibmcloudant.cloudant_v1 import CloudantV1
from ibmcloudant import CouchDbSessionAuthenticator
from ibm_cloud_sdk_core.authenticators import BasicAuthenticator
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import playsound
import os

stub = service_pb2_grpc.V2Stub(ClarifaiChannel.get_grpc_channel())

from clarifai_grpc.grpc.api import service_pb2, resources_pb2
from clarifai_grpc.grpc.api.status import status_code_pb2

# This is how you authenticate.
metadata = (('authorization', 'Key c8d7fa2e53724689afe5410443053be9'),)

# Constants for IBM COS values
COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" 
COS_API_KEY_ID = "JjY1V0AqfqgzIx2dJWMmOm4XRU1qRTxavxOomM9esKQZ" 
COS_INSTANCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/6dfc590f614b4c95a96d2aef804a1a7a:e096f891-8c52-48bf-b790-3e840afad445::" 

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

authenticator = BasicAuthenticator('apikey-v2-1t008vak1hvum8djioi3h56jygx2n1toz94zub35cmq1', '3068902af09525dc01234dfd38b6e9b4')
service = CloudantV1(authenticator=authenticator)
service.set_service_url('https://apikey-v2-1t008vak1hvum8djioi3h56jygx2n1toz94zub35cmq1:3068902af09525dc01234dfd38b6e9b4@c653534a-e3a0-46f0-b136-86453f3d9612-bluemix.cloudantnosqldb.appdomain.cloud')

authenticator = IAMAuthenticator('Gwk3oGoqIWgX7prxx1gCI_VH-G84GWA52tiULUOZSBMh')
text_to_speech = TextToSpeechV1(
    authenticator=authenticator
)

text_to_speech.set_service_url('https://api.eu-gb.text-to-speech.watson.cloud.ibm.com/instances/71d6efc1-2cd9-435a-848c-e2f231963bd6')


bucket = "projectbucket1234"
def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # set 5 MB chunks
        part_size = 1024 * 1024 * 5

        # set threadhold to 15 MB
        file_threshold = 1024 * 1024 * 15

        # set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # the upload_fileobj method will automatically execute a multi-part upload
        # in 5 MB chunks for all files over 15 MB
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))

cap = cv2.VideoCapture(0)

print(cap.isOpened())

while cap.isOpened():
    ret, frame = cap.read()
    #print(ret, frame)
    cv2.imshow('Video', frame)
    cv2.imwrite('new.jpg', frame)
    with open('new.jpg' , "rb") as f:
            file_bytes = f.read()
    request = service_pb2.PostModelOutputsRequest(
            model_id='aaa03c23b3724a16a56b629203edc62c',
            inputs=[resources_pb2.Input(data=resources_pb2.Data(image=resources_pb2.Image(base64=file_bytes)))])
    response = stub.PostModelOutputs(request, metadata=metadata)

    if response.status.code != status_code_pb2.SUCCESS:
        raise Exception("Request failed, status code: " + str(response.status.code))

   
    a= []
    for concept in response.outputs[0].data.concepts:
        if(concept.value > 0.8):
            a.append(concept.name)
    print(a)
    for i in a:
        if(i=="animal" and "wild"):
            print("detected")
            with open('hello.mp3', 'wb') as audio_file:
                audio_file.write(text_to_speech.synthesize('Alert wild animal detected beaware and safe',voice='en-GB_KateV3Voice',accept='audio/mp3').get_result().content)

            playsound.playsound('hello.mp3')
            os.remove('hello.mp3')
            print("stopped")

            while(True):
                name = datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
                cv2.imwrite(name+".jpg", frame)
                multi_part_upload(bucket, name+'.jpg', name+'.jpg')
                json_document={"link":COS_ENDPOINT+'/'+bucket+'/'+name+'.jpg'}
                response = service.post_document(db='animal', document=json_document).get_result()
                
            Key=cv2.waitKey(1)
            if Key==ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                break

