import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img


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
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']
        try:
            if msg.get('text'):
                welcome = f'<b>Hello {msg["from"]["first_name"]}!</b> &#128512;\n' \
                          f'\nWelcome to the best imageBot on Telegram.\n' \
                          f'\nYou can upload your image with a caption (like Rotate,Contour,Blur) and you will get your filter image back.\n' \
                          f'\nBy using "Concat" caption you can send 2 photos and receive them back as one photo concatenated (note that the photos must be with the exact dimensions)\n'
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
                    if res_cap.lower() == 'concat':
                        if msg.get('media_group_id') is None:
                            raise RuntimeError("You need to send 2 image's while using concat! try again &#128260;")
                        else:
                            if ImageProcessingBot.messages.get(msg['media_group_id']) is None:
                                down_img = self.download_user_photo(msg)
                                my_tele = Img(down_img)
                                ImageProcessingBot.messages[msg['media_group_id']] = down_img
                                ImageProcessingBot.cap_status = True
                            else:
                                down_img = self.download_user_photo(msg)
                                my_tele = Img(down_img)
                                my_tele.concat(Img(ImageProcessingBot.messages[msg['media_group_id']]))
                                self.send_photo(chat_id, my_tele.save_img())
                                ImageProcessingBot.cap_status = False
                    if res_cap.lower() == 'blur':
                        down_img = self.download_user_photo(msg)
                        my_tele = Img(down_img)
                        my_tele.blur()
                        self.send_photo(chat_id, my_tele.save_img())
                    if res_cap.lower() == 'contour':
                        down_img = self.download_user_photo(msg)
                        my_tele = Img(down_img)
                        my_tele.contour()
                        self.send_photo(chat_id, my_tele.save_img())
                    else:
                        raise RuntimeError('You can use only Rotate/Concat/Blur/Contour')
                else:
                    raise RuntimeError('Sorry, you need to add a caption to the image, please try again &#128260;')
            else:
                raise RuntimeError('Sorry, i know to handle only with image or text.')
        except Exception as error:
            self.send_text(chat_id, error)
