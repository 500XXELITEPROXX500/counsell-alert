import os, re, json, hashlib
from pathlib import Path
from datetime import datetime, timezone
import feedparser, requests

FEED_URLS = [
    "https://www.mlb.com/cubs/video/topic/cubs-manager-postgame",
    "https://www.mlb.com/cubs/video/topic/cubs-manager-postgame?query=counsell",
]
STATE_PATH = Path("src/state.json")

PLAYER_NAMES = [
    "Craig Counsell","Jaxon Wiggins","Dominick Reid","Josiah Wiggins",
    "Justin Steele","Ben Brown","Shota Imanaga","Cade Horton","Jordan Wicks",
    "Javier Assad","Jameson Taillon","Michael Busch","Matt Shaw",
    "Pete Crow-Armstrong","Seiya Suzuki","Dansby Swanson","Ian Happ","Kyle Tucker"
]

TOPIC_WORDS = {
    "injury": ["injury","injured","hurt","soreness","sore","strain","tightness","il"],
    "rehab": ["rehab","rehabbing","rehabilitation","assignment","recovery","throwing program"],
    "return": ["return","returns","back soon","activated","activation","timeline"],
    "role": ["role","bullpen","rotation","closer","start","starting","relief"],
    "workload": ["innings","pitch count","pitches","workload","velocity"],
}

def clean(text):
    return re.sub(r"\\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()

def load_state():
    try: return json.loads(STATE_PATH.read_text())
    except Exception: return {"seen_ids":[]}

def save_state(s):
    STATE_PATH.write_text(json.dumps(s, indent=2)+"\n")

def entry_id(e):
    raw = e.get("id") or e.get("link") or e.get("title") or repr(e)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]

def classify(text):
    low=text.lower()
    players=[p for p in PLAYER_NAMES if p.lower() in low]
    topics=[k for k,v in TOPIC_WORDS.items() if any(x in low for x in v)]
    return players,topics

def fetch_entries():
    out=[]; ids=set()
    for url in FEED_URLS:
        try:
            r=requests.get(url,timeout=20,headers={"User-Agent":"CounsellAlert/1.0"})
            r.raise_for_status()
            for e in feedparser.parse(r.content).entries:
                eid=entry_id(e)
                if eid not in ids:
                    ids.add(eid); out.append(e)
        except Exception as exc:
            print("Feed error:", exc)
    return out

def notify(title,message,link,important):
    topic=os.environ.get("NTFY_TOPIC")
    if not topic:
        print("\\n"+title+"\\n"+message+"\\n"+link)
        return
    server=os.environ.get("NTFY_SERVER","https://ntfy.sh").rstrip("/")
    headers={"Title":title[:250],"Priority":"high" if important else "default",
             "Tags":"baseball,warning" if important else "baseball",
             "Click":link,"Content-Type":"text/plain; charset=utf-8"}
    r=requests.post(f"{server}/{topic}",data=message.encode(),headers=headers,timeout=20)
    r.raise_for_status()

def main():
    state=load_state(); seen=set(state.get("seen_ids",[]))
    entries=sorted(fetch_entries(),key=lambda e:e.get("published",""))
    sent=0
    for e in entries:
        eid=entry_id(e)
        if eid in seen: continue
        title=clean(e.get("title","Craig Counsell media update"))
        summary=clean(e.get("summary","") or e.get("description",""))
        link=e.get("link","https://www.mlb.com/cubs/video/topic/cubs-manager-postgame")
        players,topics=classify(title+" "+summary)
        player_label=", ".join(players) if players else "No player identified"
        topic_label=", ".join(x.upper() for x in topics) if topics else "MEDIA"
        msg=(f"🚨 CRAIG COUNSELL MEDIA ALERT\\n\\n"
             f"Player(s): {player_label}\\nTopic: {topic_label}\\n\\n"
             f"MLB title: {title}\\n")
        if summary: msg+=f"\\nMLB source description: {summary[:900]}\\n"
        msg+=(f"\\n⚠️ Exact quote: NOT VERIFIED by this monitor.\\n"
              f"Source metadata is not presented as a verbatim quote.\\n\\n"
              f"Source: {link}\\n"
              f"Detected: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        notify(f"🚨 Counsell Alert — {title}",msg,link,bool(set(topics)&{"injury","rehab","return"}))
        seen.add(eid); sent+=1
    state["seen_ids"]=list(seen)[-500:]; save_state(state)
    print(f"Processed {len(entries)} entries; sent {sent} new alerts.")

if __name__=="__main__": main()
