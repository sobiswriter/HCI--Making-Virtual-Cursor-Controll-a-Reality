# Spatial Hand-Tracking Engine: Zero-Touch HCI

A zero-touch Human-Computer Interaction (HCI) engine that maps physical hand gestures to digital cursor inputs. This project utilizes MediaPipe’s landmark detection and OpenCV to bridge the gap between physical motion and digital input, replacing a physical mouse with a virtual, highly precise spatial system.

**Created by Soura**

---

## 🎯 Our Goal
To develop a deeply robust, touchless HCI engine that perfectly mimics the precision, reliability, and low-latency of a physical hardware mouse. We strived for absolutely **zero misclicks**, heavily customized precision deadzones, and native OS-level integration without relying on erratic or fragile computer vision assumptions.

---

## 🛠 Tech Stack
* **Python 3.x**
* **MediaPipe Tasks Vision API** (Machine Learning & 3D Hand Mesh extraction)
* **OpenCV (`cv2`)** (Image matrix processing & rendering)
* **CTypes (`user32.dll`)** (Native Windows OS hardware-level injection)
* **NumPy** (Mathematical interpolation and array manipulation)

---

## 🚀 The Journey & Project Phases

1. **Phase 1: Deep Vision Integration**
   - Transferred from legacy MediaPipe modules to the modern `HandLandmarker` Tasks API for asynchronous, high-framerate LIVE STREAM processing.
   - Built the mathematical foundation to extract 3D coordinates from the camera feed.

2. **Phase 2: Smoothing & Stabilization**
   - Addressed the "breathing jitter" problem. 
   - Implemented an Exponential Moving Average (EMA) and a **18-pixel hardware-level Deadzone Anchor** to mathematically lock the cursor in place during deliberate physical pointing.

3. **Phase 3: The Custom Gesture Engine**
   - Ripped out traditional "Euclidean pinch" assumptions, replacing them with absolute structural constraints.
   - Designed a full 3D spatially-aware measurement system that cannot be fooled by camera viewing angles or hand pitches.

4. **Phase 4: Hardware Injection**
   - Hooked up `ctypes` to bypass Python UI libs entirely and talk directly to the Windows OS kernel to simulate raw `MOUSEEVENTF_LEFTDOWN` API calls.
   - Added global F11 / F12 failsafe hooks for immediate overrides.

---

## 🧠 Mechanical Implementations (The Gestures)

We stripped away overlapping "fake dragging" timers in favor of strict, mutually exclusive structural constraints:

* **Cursor Movement (Aiming):** Make a "Finger Gun" (Index extended, Middle/Ring/Pinky curled). Aiming the pointer moves the cursor smoothly.
* **Left Click (Gun Trigger):** While in the Gun Pose, dropping your thumb tight against your index knuckle acts as a physical trigger toggle. It perfectly mimics pulling and releasing a physical mouse button.
* **Right Click (The Slap):** Radically open your hand into a fully extended "Slap." This explosive clutching-out gesture executes a Right Click.
* **Cursor Anchoring:** The millisecond a click gesture is armed, the mathematical engine hard-freezes the cursor. This entirely prevents the natural physical "jump" of your hand from displacing your pointer while executing the action!

---

## 🚧 Challenges Faced 
1. **The Twitch Factor**: When testing "Pinch to click" models, bringing two fingers together organically moved the pointer away from the target, resulting in "Drag Misclicks". **Solution:** Invented the *Cursor Anchor* physics hack.
2. **Camera Perspective Collapse**: Measuring distances using 2D image formats resulted in extreme unreliability whenever the hand tilted up or down. **Solution:** Rewrote the entire distance engine to utilize MediaPipe's hidden `.z` index for 3-Dimensional spherical detection limits.
3. **Ghost Clicks**: Moving your hand around would randomly trigger Right / Left clicks. **Solution:** Mutually exclusive poses. The Left Click literally *jams* if your hand is not perfectly locked into a Finger Gun structure.

---

## 💻 How to Run Locally

### Prerequisites
* Windows OS (Linux/Mac require replacing the `ctypes.windll.user32` calls in the code)
* Python 3.9+
* A solid webcam

### Installation
1. Clone the repository.
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. *Important:* Ensure the `hand_landmarker.task` model file is located in the root directory alongside `main.py`.

### Running the Engine
```powershell
python main.py
```
* **F11 Key:** Toggles the diagnostic OpenCV Camera feed in the background. (Keep it closed for zero-latency performance!)
* **F12 Key:** Instantly triggers an emergency failsafe, shutting down the loop and returning control to your physical mouse.

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.