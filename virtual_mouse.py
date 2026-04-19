import cv2
import mediapipe as mp
import pyautogui
import time
import math
import screen_brightness_control as sbc

# ---------------- SETUP ---------------- #
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01
screen_w, screen_h = pyautogui.size()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils
cam = cv2.VideoCapture(0)

# ---------------- STATE ---------------- #
prev_cursor = None
dragging = False
drag_start = 0
scroll_prev_x = None
tab_prev_x = None
brightness_prev_y = None
volume_prev_y = None
alt_held = False
last_tap_time = 0
tap_count = 0
timers = {'click':0, 'volume':0, 'brightness':0, 'scroll':0, 'tab':0}

# ---------------- HELPERS ---------------- #
def is_up(tip, pip):
    return tip.y < pip.y

def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def smooth(x, y, prev, a=0.3):
    if prev is None:
        return x, y, (x, y)
    px, py = prev
    sx = px + a*(x-px)
    sy = py + a*(y-py)
    return sx, sy, (sx, sy)

def text(img, msg, c=(0,255,0)):
    cv2.putText(img, msg, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, 2)

# ---------------- DRAG ---------------- #
def drag_gesture(hand, t):
    global dragging, drag_start
    if dist(hand.landmark[4], hand.landmark[20]) < 0.05:
        if not dragging:
            if drag_start == 0:
                drag_start = t
            elif t - drag_start > 0.8:
                pyautogui.mouseDown()
                dragging = True
        return True
    else:
        if dragging:
            pyautogui.mouseUp()
            dragging = False
        drag_start = 0
    return False

# ---------------- SCROLL 🖖 ---------------- #
def scroll_gesture(hand, frame, t):
    global scroll_prev_x, timers
    if all(is_up(hand.landmark[t], hand.landmark[p]) for t,p in [(8,6),(12,10),(16,14),(20,18)]) \
       and is_up(hand.landmark[4], hand.landmark[2]) \
       and dist(hand.landmark[12], hand.landmark[16]) > 0.05:
        x = hand.landmark[9].x * frame.shape[1]
        if scroll_prev_x is None:
            scroll_prev_x = x
            return True
        dx = x - scroll_prev_x
        if abs(dx) > 8 and t - timers['scroll'] > 0.02:
            pyautogui.scroll(60 if dx > 0 else -60)
            text(frame, "🖖 Scroll UP" if dx>0 else "🖖 Scroll DOWN", (0,200,0) if dx>0 else (0,0,255))
            scroll_prev_x = x
            timers['scroll'] = t
        return True
    scroll_prev_x = None
    return False

# ---------------- ALT + TAB ✌️ ---------------- #
def alt_tab_switch(hand, frame, t):
    global tab_prev_x, alt_held, timers
    index_up  = is_up(hand.landmark[8], hand.landmark[6])
    middle_up = is_up(hand.landmark[12], hand.landmark[10])
    ring_dn   = not is_up(hand.landmark[16], hand.landmark[14])
    pinky_dn  = not is_up(hand.landmark[20], hand.landmark[18])
    if index_up and middle_up and ring_dn and pinky_dn:
        if not alt_held:
            pyautogui.keyDown('alt')
            alt_held = True
        x = hand.landmark[9].x * frame.shape[1]
        if tab_prev_x is None:
            tab_prev_x = x
            return True
        dx = x - tab_prev_x
        if abs(dx) > 25 and t - timers['tab'] > 0.6:
            if dx > 0:
                pyautogui.press('tab')
                text(frame,"✌️ Next Window",(0,200,0))
            else:
                pyautogui.keyDown('shift'); pyautogui.press('tab'); pyautogui.keyUp('shift')
                text(frame,"✌️ Previous Window",(0,0,255))
            timers['tab'] = t
            tab_prev_x = x
        return True
    if alt_held:
        pyautogui.keyUp('alt')
        alt_held = False
    tab_prev_x = None
    return False

# ---------------- VOLUME 🤟 ---------------- #
def rock_volume(hand, frame, t):
    global volume_prev_y, timers
    if is_up(hand.landmark[8], hand.landmark[6]) and is_up(hand.landmark[20], hand.landmark[18]) \
       and not is_up(hand.landmark[12], hand.landmark[10]) and not is_up(hand.landmark[16], hand.landmark[14]):
        y = hand.landmark[9].y * frame.shape[0]
        if volume_prev_y is None:
            volume_prev_y = y
            return True
        dy = y - volume_prev_y
        if abs(dy) > 15 and t - timers['volume'] > 0.25:
            if dy < 0:
                pyautogui.press("volumeup")
                text(frame,"🔊 Volume UP")
            else:
                pyautogui.press("volumedown")
                text(frame,"🔉 Volume DOWN")
            timers['volume'] = t
            volume_prev_y = y
        return True
    volume_prev_y = None
    return False

# ---------------- BRIGHTNESS 🖐️ ---------------- #
brightness_prev_y = None
def brightness(hand, frame, t):
    global brightness_prev_y, timers
    if all(is_up(hand.landmark[t], hand.landmark[p]) for t,p in [(8,6),(12,10),(16,14),(20,18)]):
        cy = hand.landmark[9].y * frame.shape[0]
        if brightness_prev_y is None:
            brightness_prev_y = cy
            return True
        dy = cy - brightness_prev_y
        if abs(dy) > 15 and t - timers['brightness'] > 0.3:
            try:
                current = sbc.get_brightness()[0]
                if dy < 0:
                    sbc.set_brightness(min(current+5,100))
                    text(frame,f"☀️ Brightness UP ({current+5})")
                else:
                    sbc.set_brightness(max(current-5,0))
                    text(frame,f"🌙 Brightness DOWN ({current-5})")
            except:
                text(frame,"Brightness Error",(0,0,255))
            timers['brightness'] = t
            brightness_prev_y = cy
        return True
    brightness_prev_y = None
    return False

# ---------------- CLICK / DOUBLE CLICK ---------------- #
def click(hand, t):
    global last_tap_time, tap_count, timers
    if dist(hand.landmark[4], hand.landmark[8]) < 0.04:
        tap_count = tap_count+1 if t-last_tap_time<0.35 else 1
        last_tap_time = t
        time.sleep(0.05)
        if tap_count == 2:
            pyautogui.doubleClick()
            tap_count = 0
        return True
    if dist(hand.landmark[4], hand.landmark[12]) < 0.04 and t - timers['click'] > 0.8:
        pyautogui.rightClick()
        timers['click'] = t
        return True
    return False

# ---------------- MAIN LOOP ---------------- #
print("🤖 AI Virtual Mouse Running (ESC to quit)")

while True:
    ok, frame = cam.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    now = time.time()

    if res.multi_hand_landmarks:
        for hand_lm in res.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS)
            idx = hand_lm.landmark[8]
            mx, my, prev_cursor = smooth(idx.x*screen_w, idx.y*screen_h, prev_cursor)

            if not scroll_gesture(hand_lm, frame, now):
                if not alt_tab_switch(hand_lm, frame, now):
                    if not drag_gesture(hand_lm, now):
                        if not rock_volume(hand_lm, frame, now):
                            if not brightness(hand_lm, frame, now):
                                click(hand_lm, now)

            if not dragging:
                pyautogui.moveTo(mx, my)

            cv2.circle(frame,(int(idx.x*frame.shape[1]),int(idx.y*frame.shape[0])),10,(0,255,255),-1)

    cv2.imshow("AI Virtual Mouse", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cam.release()
cv2.destroyAllWindows()
print("Exited Cleanly ✅")
