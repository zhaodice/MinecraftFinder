import json
import sqlite3
import time
import os
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from mcstatus import JavaServer

app = Flask(__name__)
database = sqlite3.connect("database.db", check_same_thread=False)
database.execute("PRAGMA timezone = 'Asia/Shanghai'")
try:
    database.execute("create table mcservers (id integer primary key autoincrement,address varchar(100) UNIQUE,ip text,port integer,type text,updateTime DATETIME DEFAULT CURRENT_TIMESTAMP,addTime DATETIME DEFAULT CURRENT_TIMESTAMP,data text NULL)")
except Exception:
    pass

#timedatectl set-timezone Asia/Shanghai
#zmap -o r.txt -n 100000 -p 25565
def readJson(server: JavaServer) -> None:
    data = {}
    data["online"] = False
    # Build data with responses and quit on exception
    
    try:
        status_res = server.status(tries=1)
        data["version"] = status_res.version.name
        data["protocol"] = status_res.version.protocol
        try:
            data["motd"] = status_res.description
        except Exception:
            data["motd"] = status_res.motd
        data["player_count"] = status_res.players.online
        data["player_max"] = status_res.players.max
        data["players"] = []
        if status_res.players.sample is not None:
            data["players"] = [{"name": player.name, "id": player.id} for player in status_res.players.sample]

        data["ping"] = status_res.latency
        data["online"] = True

        query_res = server.query(tries=1)  # type: ignore[call-arg] # tries is supported with retry decorator
        data["host_ip"] = query_res.raw["hostip"]
        data["host_port"] = query_res.raw["hostport"]
        data["map"] = query_res.map
        data["plugins"] = query_res.software.plugins
    except Exception:  # TODO: Check what this actually excepts
        pass
    return data

def verifyAndInsert(ip,port,mctype,scannedServer):
    address = ip+":"+str(port)
    data = readJson(JavaServer.lookup(address))
    updateTime = time.strftime("%Y-%m-%d %H:%M:%S")
    if scannedServer :
        if data['online'] :
            try:
                database.execute("insert into mcservers(address,ip,port,type,updateTime,addTime,data) values (?,?,?,?,?,?,?)", 
                    (address,ip,port,mctype,updateTime,updateTime,json.dumps(data,ensure_ascii=False))
                )
                print("Found %s !" % address)
            except Exception:
                pass
            database.commit()
    else:
        if not data['online'] :
            data = json.loads(database.execute("SELECT data FROM mcservers where address=?",(address,)).fetchall()[0][0])
            if not data['online'] :
                return
            data['online'] = False
        '''
        database.execute("replace into mcservers(address,ip,port,type,updateTime,data) values (?,?,?,?,?,?)", 
                    (address,ip,port,mctype,updateTime,json.dumps(data,ensure_ascii=False))
            )
        '''
        database.execute("UPDATE mcservers SET ip=?,port=?,type=?,updateTime=?,data=? WHERE address = ?", 
                    (ip,port,mctype,updateTime,json.dumps(data,ensure_ascii=False),address)
            )
        print("Updated %s !" % address)
        
def scanner():
    while True:
        port = 25565
        print("Scaning IPs...")
        os.system("zmap -o ip.txt -n 100000 -p %d " % port )
        with open('ip.txt', 'r', encoding='utf-8') as f:
            for ip in f.readlines():
                ip = ip.strip('\n')
                print("Verify IP...%s:%d" % (ip,port))
                verifyAndInsert(ip,port,'java',True)
def fresh():
    sql = database.execute("SELECT * FROM mcservers ORDER BY updateTime ASC;")
    datas = sql.fetchall()
    for data in datas:
        verifyAndInsert(data[2],data[3],data[4],False)

@app.route('/servers', methods=["GET"])
def serverGet():
    sql = database.execute("SELECT * FROM mcservers ORDER BY addTime DESC;")
    data = sql.fetchall()
    return jsonify(code=0,data=data)
    
    
if __name__ == '__main__':

    scannerThread=threading.Thread(target=scanner)
    scannerThread.start()
    freshThread=threading.Thread(target=fresh)
    freshThread.start()
    app.run(host='0.0.0.0', threaded=True, debug=False, port=80)
    
    
'''
@app.route('/testGet', methods=["GET"])
def calculateGet():
    print(request)
    a = request.args.get("a", 0)
    b = request.args.get("b", 0)
    c = int(a) + int(b)
    res = {"result": c}
    return jsonify(code=0,data=res)
 
@app.route('/testPost', methods=["POST"])
def calculatePost():
    params = request.form if request.form else request.json
    print(params)
    a = params.get("a", 0)
    b = params.get("b", 0)
    c = a + b
    res = {"result": c}
    return jsonify(content_type='application/json;charset=utf-8',
                   reason='success',
                   charset='utf-8',
                   status='200',
                   content=res)
 
'''  