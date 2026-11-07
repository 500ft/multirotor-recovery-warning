"""Check each motor against the RC8 transition in a firmware-timestamped log."""
from pathlib import Path
from pymavlink import mavutil

def evaluate(samples, stop_us, max_delay_us=100_000, hold_us=200_000):
    post=[(t,v) for t,v in samples if stop_us<=t<=stop_us+max_delay_us+hold_us]
    for i,(t,v) in enumerate(post):
        if t-stop_us>max_delay_us:break
        if not all(x<=1010 for x in v):continue
        held=[(u,w) for u,w in post[i:] if u<=t+hold_us]
        if held and held[-1][0]>=t+hold_us-30_000 and all(all(x<=1010 for x in w) for _,w in held):
            return dict(passed=True,latency_ms=round((t-stop_us)/1000,2),max_allowed_ms=max_delay_us/1000,hold_ms=hold_us/1000)
    return dict(passed=False,reason="All four channels did not remain stopped for the required interval within the latency limit")

def check(path, telemetry=None):
    conn=mavutil.mavlink_connection(str(path)); samples=[];stops=[];last=1000
    while True:
        msg=conn.recv_match(type=["RCIN","RCOU"])
        if msg is None:break
        if msg.get_type()=="RCIN":
            v=getattr(msg,"C8",1000)
            if v>1800 and last<=1800:stops.append(msg.TimeUS)
            last=v
        else:samples.append((msg.TimeUS,[getattr(msg,f"C{i}",2000) for i in range(1,5)]))
    conn.close()
    if telemetry is not None:samples=telemetry
    return dict(log=Path(path).name,output_source="SERVO_OUTPUT_RAW firmware timestamps" if telemetry is not None else "RCOU dataflash timestamps",checks=[evaluate(samples,t) for t in stops],
                status="evaluated" if stops else "unverified: no RC8 rising edge retained in dataflash",
                passed=all(evaluate(samples,t)["passed"] for t in stops) if stops else None)

if __name__=="__main__":
    # A low average, a transient low sample, and a late stop must all fail.
    assert not evaluate([(t,[900,900,900,1300]) for t in range(0,400_000,10_000)],0)["passed"]
    assert not evaluate([(0,[1000]*4),(20_000,[1300]*4),(300_000,[1000]*4)],0)["passed"]
    assert not evaluate([(t,[1500]*4 if t<150_000 else [1000]*4) for t in range(0,500_000,10_000)],0)["passed"]
    assert evaluate([(t,[1500]*4 if t<30_000 else [1000]*4) for t in range(0,400_000,10_000)],0)["passed"]
    print("Four stop-check cases passed")
