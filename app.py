from flask import Flask, render_template, request, redirect, session, jsonify
import secrets, hashlib, requests, os, json, certifi
from pymongo import MongoClient
from datetime import timedelta, datetime
from oauthlib.oauth2 import WebApplicationClient

RANDOM_SECRET_KEY = secrets.token_urlsafe(16)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SECRET_KEY'] = RANDOM_SECRET_KEY    

GOOGLE_CLIENT_ID = '1074884255177-45kp30rm524dfbjmjoo928oq1qbcb26f.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
app.config['GOOGLE_OAUTH2_CLIENT_ID'] = GOOGLE_CLIENT_ID
app.config['GOOGLE_OAUTH2_CLIENT_SECRET'] = GOOGLE_CLIENT_SECRET
client = WebApplicationClient(GOOGLE_CLIENT_ID)
google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
authorization_endpoint = google_provider_cfg["authorization_endpoint"]
token_endpoint = google_provider_cfg["token_endpoint"]
userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]

TOKEN_EXPIRE_TIME = 30
#MongoDB 설정
#IP WhiteList
ca = certifi.where()
murl = 'mongodb+srv://dsmeal:admin@dsmeal.x4cwh.mongodb.net/myFirstDatabase?retryWrites=true&w=majority'
clientmg = MongoClient(murl, connect=False, tlsCAFile=ca)
db = clientmg['dshs']
db['token'].create_index("createdAt", expireAfterSeconds=TOKEN_EXPIRE_TIME)

@app.errorhandler(404)
def e1(msg):
    return render_template('err.html', errcode='잘못된 접근입니다.')

@app.errorhandler(500)
def e2(msg):
    return render_template('err.html', errcode='서버 내부 오류입니다.')


def hashstring(string):
    hash_string = string
    for i in range(10):
        hash_string = hashlib.sha256(hash_string.encode()).hexdigest()
    return hash_string

def get_time():
    utcnow = datetime.utcnow()
    time_gap = timedelta(hours=9)
    kor_time = utcnow + time_gap
    return [utcnow, kor_time]

def change_tz(time):
    time_gap = timedelta(hours=9)
    kor_time = time + time_gap
    return kor_time
    

def login(id, pw):
    if 'Try' not in session:
        session['Try'] = 0
    else:
        session['Try'] = session['Try'] + 1
    if session['Try'] >= 30:
        return render_template('err.html', errcode='최대 로그인 시도 횟수를 초과하였습니다.')
    if id == '' or pw == '':
        return render_template('main.html', errcode='어떠한 칸에도 공백이 존재할 수 없습니다.')
    IDlist = list(db['user'].find({'ID' : id}))
    if len(IDlist) == 0:
        return render_template('main.html', errcode='아이디가 존재하지 않습니다.')
    if IDlist[0]['PW'] != pw:
        return render_template('main.html', errcode='비밀번호가 일치하지 않습니다.')

    session['Try'] = 0

    session['ID'] = id
    session['PW'] = pw    

    if IDlist[0]['GoogleAuth'] == False:
        errmsg = request.args.get('err')
        if str(errmsg) == 'None':
            errmsg = ''
        return render_template('glogin.html', errcode=errmsg)

    if IDlist[0]['WhiteList'] == False:
        session.clear()
        return render_template('err.html', errcode='급식 신청이 확인되지 않아, QR코드를 생성할 수 없습니다.')


    return render_template('qr.html')


#구글 로그인
@app.route('/googleauth') 
def glogin():
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.host_url.replace('http://', 'https://') + "callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    Qlist = list(db['survey'].find())
    if request.method == 'GET':
        return render_template('survey.html', Qlist=Qlist, enumerate=enumerate, len=len)
    else:
        if 'Survey' in session:
            return render_template('pass.html', succode='이미 설문에 참여하셨습니다.')

        answer = request.form
        print(list(answer))
        print(Qlist[0])

        if len(answer) != len(Qlist):
            return render_template('survey.html', Qlist=Qlist, enumerate=enumerate, errcode='모든 문항에 응답해 주세요.', len=len)
        for i in range(len(answer)):
            state = list(answer)[i][0]
            before_val = Qlist[i][state]
            db['survey'].update({'NUM': i + 1},{'$set': {state:before_val + 1}})    
        session['Survey'] = 1
        return render_template('pass.html', succode='설문 결과가 정상적으로 처리되었습니다.')

#구글 로그인
@app.route('/callback')
def getUser():
    code = request.args.get("code")
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url.replace('http://', 'https://'),
        redirect_url=request.host_url.replace('http://', 'https://') + "callback",
        code=code
    )
    
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
    client.parse_request_body_response(json.dumps(token_response.json()))
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)


    unique_id = userinfo_response.json()["sub"]
    users_name = userinfo_response.json()["name"]
    users_email = userinfo_response.json()["email"]



    IDlist = list(db['user'].find({'ID' : session['ID']}))
    if users_email.split('@')[-1] != 'dshs.kr':
        return redirect('/?err=대전대신고에서 제공하는 계정이 아닙니다.')    

    if users_name != IDlist[0]['NAME']:
        return redirect('/?err=구글 계정에 저장된 이름과 회원가입시 입력한 이름이 서로 다릅니다.')    
    db['user'].update({'ID': session['ID']},{'$set': {'GoogleAuth': True, 'UID': unique_id, 'EMAIL':users_email}}, upsert=False)    
    return redirect('/')

@app.route('/getusertoken', methods=['POST'])
def gettoken():
    if 'ID' not in session:
        return redirect('/')
    Tokenlist = list(db['token'].find({'ID' : session['ID']}))
    if len(Tokenlist) >= 1:
        return jsonify({'res':Tokenlist[0]['TOKEN'], 'expire':change_tz(Tokenlist[0]['createdAt']), 'duration':TOKEN_EXPIRE_TIME})
    else:
        IDlist = list(db['user'].find({'ID' : session['ID']}))
        uid = IDlist[0]['UID']
        random_string = secrets.token_urlsafe(16)
        New_Token = uid + str(random_string)
        Hashed_Token = hashstring(New_Token)
        db['token'].insert_one({'ID': session['ID'], 'NAME': IDlist[0]['NAME'], 'TOKEN':Hashed_Token, 'createdAt': get_time()[0]})    
        return jsonify({'res':Hashed_Token, 'expire':get_time()[1], 'duration':TOKEN_EXPIRE_TIME})

@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'GET':
        if 'ID' in session:
            return login(session['ID'], session['PW'])
        return render_template('main.html')
    elif request.method == 'POST':
        id = request.form['ID'].replace(' ', '')
        pw = request.form['PW'].replace(' ', '')
        Hashed_PW = hashstring(pw)
        return login(id, Hashed_PW)
        
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        if len(request.form) != 2:
            return render_template('register.html', errcode='모든 약관에 동의해 주세요.')
        return render_template('register1.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/adduser', methods=['POST'])
def add_user():
    name = request.form['NAME']
    id = request.form['ID']
    pw = request.form['PW']
    pwr = request.form['PWR']
    tel = request.form['TEL']
    if id.find(' ') != -1 or pw.find(' ') != -1 or name.find(' ') != -1 or tel.find(' ') != -1:
        return render_template('register1.html', errcode='어떠한 칸에도 공백이 존재할 수 없습니다.')
    if len(id) == 0:
        return render_template('register1.html', errcode='입력한 아이디를 사용할 수 없습니다.')
    if len(pw) <= 4:
        return render_template('register1.html', errcode='비밀번호는 최소 5자리이여야 합니다.')
    if pw != pwr:
        return render_template('register1.html', errcode='비밀번호가 서로 일치하지 않습니다.')
    if len(tel) != 11:
        return render_template('register1.html', errcode='전화번호를 사용할 수 없습니다.')    
    if len(list(db['user'].find({'ID' : id}))) != 0:
        return render_template('register1.html', errcode='동일한 아이디가 이미 존재합니다.')

    
    Hashed_PW = hashstring(pw)
    session['ID'] = id
    session['PW'] = Hashed_PW

    db['user'].insert_one({'ID': id, 'NAME': name, 'TEL': tel, 'TIME': get_time()[1], 'PW': Hashed_PW, 'GoogleAuth':False, 'WhiteList':False, 'UID':'', 'EMAIL':'', 'NUM':''})    
    return redirect('/')


if __name__ == '__main__':
    app.run('0.0.0.0', port=80, debug=True)