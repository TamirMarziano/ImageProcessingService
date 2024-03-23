import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
#from polybot.img_proc import Img
from img_proc import Img
import boto3
import requests
import json
import pymongo


class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text, parse_mode='HTML')

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    messages = {}
    cap_status = False

    def handle_message(self, msg):
        s3 = boto3.client('s3')
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']
        objects_names = {}
        try:
            if msg.get('text'):
                welcome = f'<b>Hello {msg["from"]["first_name"]}!</b> &#128512;\n' \
                          f'\nWelcome to the best imageBot on Telegram\n' \
                          f'\nYou can upload your image with a caption (like Rotate,Contour,Blur) and you will get your filter image back.\n' \
                          f'\nBy using "Concat" caption you can send 2 photos and receive them back as one photo concatenated (note that the photos must be with the exact dimensions)\n' \
                          f'\nBy using "Yolo" caption you can use object detection AI model and detect up to 80 objects. \n'
                self.send_text(chat_id, welcome)
            elif msg.get('photo'):
                if ImageProcessingBot.cap_status:
                    msg["caption"] = 'concat'
                res_cap = msg.get("caption")
                if type(res_cap) is str:
                    if res_cap.lower() == 'rotate':
                        down_img = self.download_user_photo(msg)
                        my_tele = Img(down_img)
                        my_tele.rotate()
                        self.send_photo(chat_id, my_tele.save_img())
                    elif res_cap.lower() == 'concat':
                        if msg.get('media_group_id') is None:
                            raise RuntimeError("You need to send 2 image's while using concat! try again &#128260;")
                        else:
                            if ImageProcessingBot.messages.get(msg['media_group_id']) is None:
                                down_img = self.download_user_photo(msg)
                                ImageProcessingBot.messages[msg['media_group_id']] = down_img
                                ImageProcessingBot.cap_status = True
                            else:
                                down_img = self.download_user_photo(msg)
                                my_tele = Img(down_img)
                                my_tele2 = Img(ImageProcessingBot.messages[msg['media_group_id']])
                                ImageProcessingBot.cap_status = False
                                my_tele2.concat(my_tele)
                                self.send_photo(chat_id, my_tele2.save_img())
                    elif res_cap.lower() == 'blur':
                        down_img = self.download_user_photo(msg)
                        my_tele = Img(down_img)
                        my_tele.blur()
                        self.send_photo(chat_id, my_tele.save_img())
                    elif res_cap.lower() == 'contour':
                        down_img = self.download_user_photo(msg)
                        my_tele = Img(down_img)
                        my_tele.contour()
                        self.send_photo(chat_id, my_tele.save_img())
                    elif res_cap.lower() == 'yolo':
                        img_name = msg['photo'][1]['file_unique_id']+'.jpeg'
                        response = s3.list_objects_v2(Bucket='tamirmarzbuc')
                        if 'Contents' in response:
                            for obj in response['Contents']:
                                objects_names[obj['Key']] = True
                            if objects_names.get(img_name):
                                mongo_client = 'mongodb://mongo1:27017,mongo2:27017,mongo3:27017/mydb?replicaSet=myReplicaSet'
                                client = pymongo.MongoClient(mongo_client)
                                mydb = client["mydb"]
                                mycoll = mydb["predictions"]
                                query = {'original_img_path': f'/{img_name}'}
                                result = mycoll.find(query)
                                for document in result:
                                    document = document.get('labels')
                                    objects = {}
                                    detec = 'Detected objects:'
                                    for i in range(len(document)):
                                        if objects.get(document[i]['class']) is None:
                                            objects[document[i]['class']] = 1
                                        else:
                                            objects[document[i]['class']] += 1
                                    for key, value in objects.items():
                                        detec = detec + f'\n {key}: {value}'
                                    self.send_text(chat_id, detec)
                            else:
                                down_img = self.download_user_photo(msg)
                                s3.upload_file(down_img, 'tamirmarzbuc', img_name)
                                x = requests.post(f'http://yoloapp:8081/predict?imgName={img_name}')
                                x = x.text
                                x = json.loads(x)
                                x = x.get('labels')
                                objects = {}
                                detec = 'Detected objects:'
                                for i in range(len(x)):
                                    if objects.get(x[i]['class']) is None:
                                        objects[x[i]['class']] = 1
                                    else:
                                        objects[x[i]['class']] += 1
                                for key, value in objects.items():
                                    detec = detec + f'\n {key}: {value}'
                                self.send_text(chat_id, detec)
                        else:
                            down_img = self.download_user_photo(msg)
                            s3.upload_file(down_img, 'tamirmarzbuc', img_name)
                            x = requests.post(f'http://yoloapp:8081/predict?imgName={img_name}')
                            x = x.text
                            x = json.loads(x)
                            x = x.get('labels')
                            objects = {}
                            detec = 'Detected objects:'
                            for i in range(len(x)):
                                if objects.get(x[i]['class']) is None:
                                    objects[x[i]['class']] = 1
                                else:
                                    objects[x[i]['class']] += 1
                            for key, value in objects.items():
                                detec = detec + f'\n {key}: {value}'
                            self.send_text(chat_id, detec)
                    else:
                        raise RuntimeError('You can use only Rotate/Concat/Blur/Contour/Yolo')
                else:
                    raise RuntimeError('Sorry, you need to add a caption to the image, please try again &#128260;')
            else:
                raise RuntimeError('Sorry, i know to handle only with image or text.')
        except Exception as error:
            self.send_text(chat_id, error)
