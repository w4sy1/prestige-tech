"""Detached Ed25519 signatures. Trust comes from the separately supplied public key."""
import base64
import hashlib
import os
from pathlib import Path
from runtime import atomic_json,read_json


def modules():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        return serialization,Ed25519PrivateKey,Ed25519PublicKey,InvalidSignature
    except ImportError:raise RuntimeError('Podpisy wymagają pakietu cryptography z requirements-signing.txt.') from None


def new_key(private_path,public_path):
    serialization,Private,_,_=modules()
    private_path=Path(private_path);public_path=Path(public_path)
    password=os.environ.get('PRESTIGE_SIGNING_PASSWORD','').encode('utf-8')
    if len(password)<12:raise ValueError('Ustaw PRESTIGE_SIGNING_PASSWORD (minimum 12 bajtów) w środowisku.')
    if private_path.resolve()==public_path.resolve() or private_path.exists() or public_path.exists():raise ValueError('Wskaż dwa różne, nowe pliki kluczy.')
    key=Private.generate()
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.BestAvailableEncryption(password))
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    private_path.parent.mkdir(parents=True,exist_ok=True);public_path.parent.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(private_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(descriptor,'wb') as stream:stream.write(private)
    with public_path.open('xb') as stream:stream.write(public)
    return {'private_key':str(private_path),'public_key':str(public_path),'encrypted':True}


def sign(file,key_path,signature_path):
    serialization,Private,_,_=modules()
    if Path(signature_path).exists():raise FileExistsError('Podpis już istnieje.')
    password=os.environ.get('PRESTIGE_SIGNING_PASSWORD','').encode('utf-8')
    key=serialization.load_pem_private_key(Path(key_path).read_bytes(),password=password or None)
    if not isinstance(key,Private):raise ValueError('Wymagany klucz Ed25519.')
    digest=hashlib.sha256(Path(file).read_bytes()).digest()
    atomic_json(signature_path,{'schema_version':1,'algorithm':'Ed25519-SHA256','sha256':digest.hex(),
        'signature':base64.b64encode(key.sign(b'PrestigeTech-manifest-v1\0'+digest)).decode('ascii')})
    return {'signed':True,'signature_file':str(signature_path)}


def verify(file,public_path,signature_path):
    serialization,_,Public,InvalidSignature=modules()
    record=read_json(signature_path)
    if record.get('schema_version')!=1 or record.get('algorithm')!='Ed25519-SHA256':raise ValueError('Nieobsługiwany podpis.')
    key=serialization.load_pem_public_key(Path(public_path).read_bytes())
    if not isinstance(key,Public):raise ValueError('Wymagany klucz publiczny Ed25519.')
    digest=hashlib.sha256(Path(file).read_bytes()).digest()
    if digest.hex()!=record.get('sha256'):return {'ok':False,'reason':'Zmieniono treść pliku.'}
    try:key.verify(base64.b64decode(record['signature'],validate=True),b'PrestigeTech-manifest-v1\0'+digest)
    except InvalidSignature:return {'ok':False,'reason':'Podpis nie pasuje do zaufanego klucza.'}
    return {'ok':True,'algorithm':record['algorithm'],'note':'Weryfikacja dotyczy klucza podanego osobno, nie tożsamości autora klucza.'}


def add_arguments(parser):
    parser.add_argument('--private-key');parser.add_argument('--public-key');parser.add_argument('--signature')


def handle(args,file):
    if args.command=='keygen':
        if not args.private_key or not args.public_key:raise ValueError('Podaj --private-key i --public-key.')
        return new_key(args.private_key,args.public_key)
    if not file or not args.signature:raise ValueError('Podaj plik manifestu/baseline oraz --signature.')
    if args.command=='sign':
        if not args.private_key:raise ValueError('Podaj --private-key.')
        return sign(file,args.private_key,args.signature)
    if not args.public_key:raise ValueError('Podaj --public-key z zaufanego źródła.')
    return verify(file,args.public_key,args.signature)
