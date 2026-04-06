import cv2
import mediapipe as mp
import time
import numpy as np
import math
import ctypes
import keyboard
import sys

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# Global variable to store the result asynchronously
latest_result = None

# EMA Filter variables
smoothed_x, smoothed_y = None, None

# Screen mapping properties
SCREEN_W, SCREEN_H = 1920, 1080
FRAME_MARGIN = 0.25 

# Click States
trigger_pulled = False
trigger_pull_time = 0

right_pinch_pulled = False
right_pinch_time = 0

# OS Mouse API Constants
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

# Option to show camera feed
SHOW_PREVIEW = False 

def get_result(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_result
    latest_result = result

def draw_landmarks_manual(frame, landmarks):
    h, w, c = frame.shape
    CONNECTIONS = [
        (0,1), (1,2), (2,3), (3,4),       # Thumb
        (0,5), (5,6), (6,7), (7,8),       # Index
        (5,9), (9,10), (10,11), (11,12),  # Middle
        (9,13), (13,14), (14,15), (15,16),# Ring
        (13,17), (0,17), (17,18), (18,19), (19,20) # Pinky
    ]
    for connection in CONNECTIONS:
        pt1 = landmarks[connection[0]]
        pt2 = landmarks[connection[1]]
        x1, y1 = int(pt1.x * w), int(pt1.y * h)
        x2, y2 = int(pt2.x * w), int(pt2.y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    for lm in landmarks:
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

def calculate_distance(lm1, lm2):
    # Upgraded to complete 3D Spatial Distance (X, Y, Z) 
    # This prevents hand-tilts or wrist pitches from destroying the measurement!
    return math.sqrt((lm1.x - lm2.x)**2 + (lm1.y - lm2.y)**2 + (lm1.z - lm2.z)**2)

def get_finger_states(landmarks):
    # True means Curled. False means Extended.
    states = {}
    finger_joints = {'index': (8, 6), 'middle': (12, 10), 'ring': (16, 14), 'pinky': (20, 18)}
    wrist = landmarks[0]
    for name, (tip, pip) in finger_joints.items():
        states[name] = calculate_distance(landmarks[tip], wrist) < calculate_distance(landmarks[pip], wrist)
    return states

def check_thumb_curled(landmarks):
    # By upgrading to 3D, the thumb's actual depth is measured.
    palm_width = calculate_distance(landmarks[5], landmarks[17])
    dist_thumb_to_index_base = calculate_distance(landmarks[4], landmarks[5])
    
    # Relaxed to 55% spatial volume to cleanly capture the thumb curling down against the knuckle
    # regardless of physical hand shape or thickness, while still blocking micro-shake false positives.
    return dist_thumb_to_index_base < (palm_width * 0.55)

def check_thumb_index_pinch(landmarks):
    # Calculates distance between Index Tip (8) and Thumb Tip (4)
    dist_thumb_to_index_tip = calculate_distance(landmarks[4], landmarks[8])
    palm_width = calculate_distance(landmarks[5], landmarks[17])
    
    # Needs to be a very tight pinch to avoid misclicks while aiming
    return dist_thumb_to_index_tip < (palm_width * 0.35)

def main():
    global smoothed_x, smoothed_y, SHOW_PREVIEW
    global trigger_pulled, trigger_pull_time
    global right_pinch_pulled, right_pinch_time

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path='hand_landmarker.task'),
        running_mode=VisionRunningMode.LIVE_STREAM,
        result_callback=get_result,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.7
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Background tracking running... Press F11 to toggle camera view. Press F12 ANYWHERE to trigger FAILSAFE and emergency exit.")

    with HandLandmarker.create_from_options(options) as landmarker:
        start_time = time.time()
        while True:
            if keyboard.is_pressed('f12'):
                print("\n[FAILSAFE TRIGGERED] Terminating script and returning mouse control...")
                sys.exit()
                
            if keyboard.is_pressed('f11'):
                SHOW_PREVIEW = not SHOW_PREVIEW
                if not SHOW_PREVIEW:
                    cv2.destroyAllWindows()
                time.sleep(0.3) 

            success, frame = cap.read() 
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            frame_timestamp_ms = int((time.time() - start_time) * 1000)
            landmarker.detect_async(mp_image, frame_timestamp_ms)

            if latest_result and latest_result.hand_landmarks:
                for landmarks in latest_result.hand_landmarks:
                    if SHOW_PREVIEW:
                        draw_landmarks_manual(frame, landmarks)
                    
                    index_tip = landmarks[8]
                    
                    h, w, c = frame.shape
                    
                    box_left = FRAME_MARGIN
                    box_right = 1.0 - FRAME_MARGIN
                    box_top = FRAME_MARGIN
                    box_bottom = 1.0 - FRAME_MARGIN

                    if SHOW_PREVIEW:
                        cv2.rectangle(frame, 
                                      (int(box_left * w), int(box_top * h)), 
                                      (int(box_right * w), int(box_bottom * h)), 
                                      (255, 0, 0), 2)

                    raw_screen_x = np.interp(index_tip.x, [box_left, box_right], [0, SCREEN_W])
                    raw_screen_y = np.interp(index_tip.y, [box_top, box_bottom], [0, SCREEN_H])

                    # ---------------- GESTURE DEFINITIONS ---------------- 
                    finger_states = get_finger_states(landmarks)
                    
                    is_index_extended = not finger_states['index']
                    is_middle_curled = finger_states['middle']
                    is_ring_curled = finger_states['ring']
                    is_pinky_curled = finger_states['pinky']

                    # The Poses
                    is_gun_pose = is_index_extended and is_middle_curled and is_ring_curled and is_pinky_curled

                    # Mutual Exclusion Checks for the Thumb
                    is_thumb_curled_to_knuckle = check_thumb_curled(landmarks)
                    is_thumb_pinched_to_index = check_thumb_index_pinch(landmarks)
                    
                    # Ensure they cannot both be true simultaneously (prioritize left click if both somehow trigger)
                    if is_thumb_curled_to_knuckle and is_thumb_pinched_to_index:
                        is_thumb_pinched_to_index = False

                    # The Core Action Triggers
                    is_left_click_action = is_gun_pose and is_thumb_curled_to_knuckle
                    is_right_click_action = is_gun_pose and is_thumb_pinched_to_index
                    
                    # ---------------- CURSOR ANCHORING FOR GESTURE PRECISION ----------------
                    # Freeze the cursor during physical execution of clicks to prevent index-drop jumps
                    is_executing_gesture = trigger_pulled or right_pinch_pulled or is_left_click_action or is_right_click_action
                    
                    if is_executing_gesture and smoothed_x is not None:
                        raw_screen_x, raw_screen_y = smoothed_x, smoothed_y # HARD LOCK

                    # ---------------- OS CURSOR SMOOTHING + DEADZONE ----------------
                    if smoothed_x is None:
                        smoothed_x, smoothed_y = raw_screen_x, raw_screen_y
                    else:
                        dist_moved = math.hypot(raw_screen_x - smoothed_x, raw_screen_y - smoothed_y)
                        
                        if dist_moved < 18.0:
                            pass
                        else:
                            dynamic_alpha = 0.05 + min((dist_moved - 18) / 400.0, 0.4) 
                            smoothed_x = dynamic_alpha * raw_screen_x + (1 - dynamic_alpha) * smoothed_x
                            smoothed_y = dynamic_alpha * raw_screen_y + (1 - dynamic_alpha) * smoothed_y
                    
                    ctypes.windll.user32.SetCursorPos(int(smoothed_x), int(smoothed_y))

                    # ---------------- LEFT CLICK LOGIC (PULL & RELEASE TAPPING) ---------------- 
                    if is_left_click_action:
                        if not trigger_pulled:
                            trigger_pulled = True
                            trigger_pull_time = time.time()
                            print("LEFT TRIGGER ARMED...")
                    else:
                        if trigger_pulled:
                            duration = time.time() - trigger_pull_time
                            
                            # Fire constraints: Hand must still be in strict Gun Pose, and physical tap rapid
                            if is_gun_pose and duration < 0.6: 
                                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                print("LEFT CLICK FIRED (Perfect Pull & Release)")
                            else:
                                print("LEFT TRIGGER CANCELLED (Slow pull or pose broken)")
                            trigger_pulled = False

                    # ---------------- RIGHT CLICK LOGIC (INDEX-THUMB PINCH RELEASE) ---------------- 
                    if is_right_click_action:
                        if not right_pinch_pulled:
                            right_pinch_pulled = True
                            right_pinch_time = time.time()
                            print("RIGHT PINCH ARMED...")
                    else:
                        if right_pinch_pulled:
                            duration = time.time() - right_pinch_time
                            
                            # Fire constraints: Must return to standard Gun Pose rapidly (< 0.6s)
                            if is_gun_pose and duration < 0.6: 
                                ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                                ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                                print("RIGHT CLICK FIRED (Pinch Perfect Release)")
                            elif duration >= 0.6:
                                print("RIGHT PINCH CANCELLED (Waited too long)")
                                
                            right_pinch_pulled = False

                    # ---------------- VISUAL DIAGNOSTICS ---------------- 
                    if SHOW_PREVIEW:
                        vis_x = int(np.interp(smoothed_x, [0, SCREEN_W], [0, w]))
                        vis_y = int(np.interp(smoothed_y, [0, SCREEN_H], [0, h]))
                        
                        circle_color = (0, 0, 255) # Red default (Hover)
                        if right_pinch_pulled:
                            circle_color = (255, 0, 255) # Purple/Magenta (Right Pinch Armed)
                        elif trigger_pulled:
                            circle_color = (0, 255, 0) # Green (Left Trigger Armed)
                        elif is_gun_pose and not is_thumb_curled_to_knuckle and not is_thumb_pinched_to_index:
                            circle_color = (0, 255, 255) # Yellow (Gun aimed, trigger ready)
                        
                        cv2.circle(frame, (vis_x, vis_y), 10, circle_color, -1)

            if SHOW_PREVIEW:
                cv2.imshow('Hand Tracking Analysis', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()