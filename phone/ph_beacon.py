#!/usr/bin/env python3
# ph_beacon v3 (2026-09-09): F1 fix — last-known-URL retention (never publish empty url),
# + healthy flag, adb() stderr-clean + exact device match (F9). Retained + self-heal (v2 base).
import os, json, time, hmac, hashlib, uuid, re, subprocess, urllib.request
import paho.mqtt.client as mqtt
SID="53cf4a5803c91726b892e5d0785085c6"
KEY=open(os.path.expanduser("~/arenabridge/arenabridge.key")).read().strip()
T=f"arenabridge/{SID}/ph/pres"
CF=os.path.expanduser("~/zillion_pw/cf.log")
FB=os.path.expanduser("~/zillion_pw/fallback.log")
LAST_URL=""
LAST_GOOD_TS=0.0
def sign(s): return hmac.new(KEY.encode(), s.encode(), hashlib.sha256).hexdigest()
def env(obj):
    d=json.dumps(obj,separators=(",",":")); return json.dumps({"d":d,"h":sign(d)})
def found(path,pat):
    try:
        xs=re.findall(pat,open(path,errors="ignore").read()); return xs[-1] if xs else ""
    except Exception: return ""
def healthy(u):
    if not u: return False
    try:
        with urllib.request.urlopen(u+"/ping",timeout=5) as r: return r.status==200
    except Exception: return False
def url():
    # F1: never return "" — keep last-known; caller sees healthy flag + age
    global LAST_URL, LAST_GOOD_TS
    cf=found(CF,r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    fb=found(FB,r"https://[a-zA-Z0-9-]+\.lhr\.life")
    for u in (cf,fb):
        if healthy(u):
            LAST_URL=u; LAST_GOOD_TS=time.time(); return u
    return LAST_URL
def adb():
    try:
        o=subprocess.run(["adb","devices"],capture_output=True,text=True,timeout=5).stdout
        for ln in o.splitlines():
            f=ln.split()
            if len(f)==2 and f[1]=="device": return f[0]
    except Exception: pass
    return ""
def main():
    global LAST_URL
    while True:
        try:
            try: cl=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="phbe_"+uuid.uuid4().hex[:6])
            except Exception: cl=mqtt.Client(client_id="phbe_"+uuid.uuid4().hex[:6])
            cl.reconnect_delay_set(1,30)
            cl.connect("broker.emqx.io",1883,60); cl.loop_start()
            n=0
            while True:
                u=url()
                info=cl.publish(T,env({"role":"phone","ver":"ph-supervisor-v3","online":True,
                    "url":u,"healthy":bool(u and u in (found(CF,r"https://[a-zA-Z0-9-]+\.trycloudflare\.com"),found(FB,r"https://[a-zA-Z0-9-]+\.lhr\.life")) and healthy(u)),
                    "adb":adb(),"ts":time.time(),"url_age":round(time.time()-LAST_GOOD_TS,1) if LAST_GOOD_TS else None}),qos=1,retain=True)
                if info.rc!=0: raise RuntimeError("publish rc=%d"%info.rc)
                n+=1
                if n%120==0: raise RuntimeError("periodic reconnect")
                time.sleep(15)
        except Exception:
            try: cl.loop_stop(); cl.disconnect()
            except Exception: pass
            time.sleep(10)
if __name__=="__main__": main()
