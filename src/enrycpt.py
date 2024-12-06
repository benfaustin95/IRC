import opcode
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import pickle
from message import *
from pathlib import Path

"""
---------------------------------- Encryption Background Info----------------------------------------
 
AES Key

    The AES key is a secret key used in the AES (Advanced Encryption Standard) algorithm to encrypt and decrypt data.
    It can be 128, 192, or 256 bits long.
    The key is mandatory for the encryption process as it determines the output of the encryption.
    Without the correct key, decrypting the data back to its original form is practically impossible.

Initialization Vector (IV)

    The IV is a random or pseudo-random value used in conjunction with the AES key to ensure that the same plaintext 
    will encrypt to different ciphertexts each time.  The IV is particularly important in modes of operation like CBC 
    (Cipher Block Chaining) and GCM (Galois/Counter Mode).  It introduces randomness into the encryption process,
    preventing identical plaintext blocks from producing identical ciphertext blocks.

How They Work Together

    When encrypting data, the AES algorithm uses both the key and the IV.
    The key is used to perform the actual encryption, while the IV ensures that the encryption is non-deterministic.
    For example, in CBC mode, the IV is XORed with the first block of plaintext before encryption.
    This ensures that even if two plaintexts are identical, their ciphertexts will differ if different IVs are used.
    The IV does not need to be kept secret, but it must be unique and unpredictable for each encryption session to
    maintain security.

Security Info

    Using the same IV for multiple encryption's with the same key can lead to vulnerabilities, as it can allow attackers
    to detect patterns and potentially decrypt the data. Therefore, it is a best practice to generate a new, random IV 
    for each  encryption operation and store it alongside the ciphertext.  This way, it can be used during decryption
    to retrieve the original plaintext.
    
Our Implementation

     Our program uses a shared AES key for both encryption and decryption between the server and client. 
     We store this AES key in the environment variables of both programs and retrieve it when needed for encryption and
     decryption operations. For each encryption operation, we use the AES key to encrypt the payload. Each operation 
     also involves generating a unique and random Initialization Vector (IV) to ensure that even if the same plaintext 
     is encrypted multiple times, the resulting ciphertext will be different each time. The IV is sent along with the 
     encrypted payload to the recipient, who uses it to decrypt the payload. It's important to note again that the IV 
     does not need to be kept secret, but it must be unique and random for each encryption session to maintain security.
     Encryption is most susceptible if the AES key is used to encrypt the payload that is stored in the .encryption file
     is made aware to any one. For the program it is only ever loaded in as a environment variable and called and declared
     as a variable in limited method scopes, never longer than need.
"""


class Private_Message(Message):

    def __init__(self, opcode, payload):
        self.header = None
        self.payload = None

        if opcode and payload:
            keys = ['target_user', 'message', 'iv','sender']
            encrypted_data = self.encrypt_data(payload['target_user'], payload['message'],payload['sender'])

            self.payload = dict(zip(keys, encrypted_data))

            self.header = Header(opcode, self.crc32())


    """Helper Method to Set data of class"""
    def set_data(self, msg_obj):
        self.header = msg_obj.header
        self.payload = msg_obj.payload

    """ Get root filepath project """
    def get_project_root(self) -> Path:
        #NOTE: Project root must be the directory containing the 'src' folder
        return Path(__file__).parent.parent

    """ Get the complete file path """
    def get_encryption_file_path(self) -> Path:
        project_root = self.get_project_root()
        file_path = project_root / 'src' / '.encryption'
        return file_path

    """Load environment variables from a .env file."""
    def load_env_file(self):

        file_path = self.get_encryption_file_path()

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The .encryption file was not found at {file_path}")

        with open(file_path) as f:
            for line in f:

                line = line.strip()

                # Split key-value pairs
                key, _, value = line.partition('=')

                # Set the environment variable
                os.environ[key] = value
                encoded_key_from_env = os.getenv('AES_KEY')

                if encoded_key_from_env is None:
                    return False, "AES_KEY environment variable  not found"
                else:
                    return encoded_key_from_env


    """ Encrypt payload & target_nickname with a random IV"""
    def encrypt_data(self, payload, target_nickname,sender):
        # Retrieve the encoded key from environment variables
        encoded_key_from_env = self.load_env_file()

        # Decode the base64 encoded key back to bytes
        key = base64.b64decode(encoded_key_from_env)

        # Generate a random IV for each encryption
        iv = os.urandom(16)

        # Create a Cipher object using the AES algorithm in CBC mode
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))

        # Create separate encryptor objects for each encryption
        encryptor_p = cipher.encryptor()
        encryptor_n = cipher.encryptor()
        encryptor_s = cipher.encryptor()

        # Pad the payload
        padder_payload = padding.PKCS7(algorithms.AES.block_size).padder()
        byte_s_payload = payload.encode("utf-8")
        padded_payload = padder_payload.update(byte_s_payload) + padder_payload.finalize()

        # Pad the target_nickname
        padder_nickname = padding.PKCS7(algorithms.AES.block_size).padder()
        byte_s_target_nickname = target_nickname.encode("utf-8")
        padded_target_nickname = padder_nickname.update(byte_s_target_nickname) + padder_nickname.finalize()

        # Pad the sender
        padder_sender = padding.PKCS7(algorithms.AES.block_size).padder()
        byte_s_sender = sender.encode("utf-8")
        padded_sender = padder_sender.update(byte_s_sender) + padder_sender.finalize()

        # Encrypt the padded messages
        encrypted_payload = encryptor_p.update(padded_payload) + encryptor_p.finalize()
        encrypted_target_nickname = encryptor_n.update(padded_target_nickname) + encryptor_n.finalize()
        encrypted_sender = encryptor_s.update(padded_sender) + encryptor_s.finalize()

        return encrypted_payload, encrypted_target_nickname, iv, encrypted_sender

    def decrypt_message(self):
        # Retrieve the encoded key from environment variables
        encoded_key_from_env = self.load_env_file()

        # Decode the base64 encoded key back to bytes
        key = base64.b64decode(encoded_key_from_env)
        cipher = Cipher(algorithms.AES(key), modes.CBC(self.payload['iv']))

        # Create a decryptor object to perform decryption
        decryptor = cipher.decryptor()

        # Decrypt the ciphertext
        decrypted_data = decryptor.update(self.payload['message']) + decryptor.finalize()

        # Remove padding after decryption
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()

        # Decode the plaintext
        decrypted_payload = unpadded_data.decode("utf-8")
        return decrypted_payload

    def decrypt_target_user(self):
        # Retrieve the encoded key from environment variables encoded_key_from_env = self.load_env_file()
        encoded_key_from_env = self.load_env_file()

        # Decode the base64 encoded key back to bytes
        key = base64.b64decode(encoded_key_from_env)

        # Create a Cipher object using the AES algorithm in CBC mode
        cipher = Cipher(algorithms.AES(key), modes.CBC(self.payload['iv']))

        # Create a decryptor object to perform decryption
        decryptor = cipher.decryptor()

        # Decrypt the ciphertext
        decrypted_data = decryptor.update(self.payload['target_user']) + decryptor.finalize()

        # Remove padding after decryption
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()

        # Decode the plaintext
        decrypted_target_nickname = unpadded_data.decode("utf-8")
        return decrypted_target_nickname

    def decrypt_sender(self):
        # Retrieve the encoded key from environment variables
        encoded_key_from_env = self.load_env_file()

        # Decode the base64 encoded key back to bytes
        key = base64.b64decode(encoded_key_from_env)

        # Create a Cipher object using the AES algorithm in CBC mode
        cipher = Cipher(algorithms.AES(key), modes.CBC(self.payload['iv']))

        # Create a decryptor object to perform decryption
        decryptor = cipher.decryptor()

        # Decrypt the ciphertext
        decrypted_data = decryptor.update(self.payload['sender']) + decryptor.finalize()

        # Remove padding after decryption
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()

        # Decode the plaintext
        decrypted_sender_nickname = unpadded_data.decode("utf-8")
        return decrypted_sender_nickname

    "Method to be invoked by client up receive of Private MMessage class"
    def decrypt_data(self):
        return f"'sender': {self.decrypt_sender()}, 'message': '{self.decrypt_message()}'"

