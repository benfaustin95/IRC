import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

"""Load environment variables from a .env file."""
def load_env_file(file_path):
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

# Path to the .env file located at 'repo/src/.env'
env_file_path = os.path.join(os.getcwd(), '.env')
load_env_file(env_file_path)

# Encrypt a message with a random IV
def encrypt_message(plaintext):
    # Retrieve the encoded key from environment variables
    encoded_key_from_env = os.getenv('AES_KEY')
    if encoded_key_from_env is None:
        raise ValueError("AES_KEY environment variable is not set")

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
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    # Return both the IV and the ciphertext
    return iv, ciphertext

# Decrypt a message using the provided IV
def decrypt_message(iv, ciphertext):
    # Retrieve the encoded key from environment variables
    encoded_key_from_env = os.getenv('AES_KEY')
    if encoded_key_from_env is None:
        raise ValueError("AES_KEY environment variable is not set")

    # Decode the base64 encoded key back to bytes
    key = base64.b64decode(encoded_key_from_env)

    # Create a Cipher object using the AES algorithm in CBC mode
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))

    # Create a decryptor object to perform decryption
    decryptor = cipher.decryptor()

    # Decrypt the ciphertext back to plaintext
    decrypted_text = decryptor.update(ciphertext) + decryptor.finalize()

    return decrypted_text

# Example usage
plaintext = b"a secret message"

# Encrypt the message
iv, ciphertext = encrypt_message(plaintext)

# Decrypt the message
decrypted_text = decrypt_message(iv, ciphertext)

# Print the original, encrypted, and decrypted messages
print("Original:", plaintext)
print("Encrypted:", ciphertext)
print("Decrypted:", decrypted_text)
