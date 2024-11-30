import opcode
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import pickle
from message import *

"""
AES Key

    The AES key is a secret key used in the AES (Advanced Encryption Standard) algorithm to encrypt and decrypt data.
    It can be 128, 192, or 256 bits long.
    The key is crucial for the encryption process as it determines the output of the encryption.
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

Security Implications

    Using the same IV for multiple encryptions with the same key can lead to vulnerabilities, as it can allow attackers
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
"""
class Private_Message:

    def __init__(self, opcode, payload):
        self.header = Header(opcode, self.crc32(payload))
        self.payload , self.iv = self.encrypt_message(payload)

    def crc32(self, payload):
        c = zlib.crc32(str(payload).encode("utf-8"))
        return c

    def serialize(self):
        serialized_message = pickle.dumps(self)
        return len(serialized_message).to_bytes(MAX_MSG_BYTES, byteorder='big'), serialized_message

    """Load environment variables from a .env file."""
    def load_env_file(self):

        file_path  = os.path.join(os.getcwd(), '.encryption')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The .env file was not found at {file_path}")

        with open(file_path) as f:
            for line in f:
                # Strip whitespace and ignore comments or empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Split key-value pairs
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")  # Remove surrounding quotes

                # Set the environment variable
                os.environ[key] = value
                encoded_key_from_env = os.getenv('AES_KEY')

                if encoded_key_from_env is None:
                    return False , "AES_KEY environment variable is not set"
                else:
                    return encoded_key_from_env

    # Path to the .env file located at '[cwd]/src/.env'

    # Encrypt a message with a random IV
    def encrypt_message(self,payload):

        # Retrieve the encoded key from environment variables
        encoded_key_from_env = self.load_env_file()

        # Decode the base64 encoded key back to bytes
        key = base64.b64decode(encoded_key_from_env)

        # Generate a random IV for each encryption
        iv = os.urandom(16)
        print("Generated IV:", iv)  # Print the generated IV for verification

        # Create a Cipher object using the AES algorithm in CBC mode
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))

        # Create an encryptor object to perform encryption
        encryptor = cipher.encryptor()

        # Encrypt the plaintext message
        # Note: Ensure the plaintext is padded to a multiple of the block size if necessary
        byte_s_payload = payload.encode("utf-8")

        encrypted_payload = encryptor.update(byte_s_payload) + encryptor.finalize()

        print("Encrypted Payload:", encrypted_payload)
        return encrypted_payload, iv


    """ Decrypt a message using the provided IV """
    def decrypt_message(self):
        # Retrieve the encoded key from environment variables
        encoded_key_from_env = self.load_env_file()

        # Decode the base64 encoded key back to bytes
        key = base64.b64decode(encoded_key_from_env)

        # Create a Cipher object using the AES algorithm in CBC mode
        cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv))

        # Create a decryptor object to perform decryption
        decryptor = cipher.decryptor()

        plaintext = self.payload
        # Decrypt the ciphertext back to plaintext
        byte_s_payload = decryptor.update(plaintext) + decryptor.finalize()

        self.payload = byte_s_payload.decode("utf-8")
        print("Payload:", self.payload)



# ----- Example  ------
plaintext = "a secret message"
msg = Private_Message(1, payload=plaintext)
pickled_data = pickle.dumps(msg)
print(pickled_data)
pickle.loads(pickled_data)
msg.decrypt_message()