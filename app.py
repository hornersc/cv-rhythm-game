"""
Hand Dance
Created by Casey Horner, starting 11/5/2022, in an attempt to make a camera vision rhythm game.
Contact at mail.horner.sc@gmail.com


DISCLAIMER: This code was developed in an experimental and exploratory fashion, with organization taking a backseat. Hopefully it will improve over time.

TO DO:
- graphics
    - main icon
    - hands
    - additional effects
- menus
    - gui
- code clean up
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import math
import pygame
import datetime
import json

from collections import deque

import cv2 as cv
import mediapipe as mp

def main():
    running = True
    cap_width = 960
    cap_height = 540
    pygame.display.set_icon(pygame.image.load("logo.ico"))
    pygame.display.set_caption('Hand Dance')
    levels_path = "./levels/"
    songs_path = "./songs/"
    sfx_path = "./sfx/"
    default_song_name = "twinkle-twinkle-little-star.mp3"
    preferences_path = "preferences.json"
    start_coords = [cap_width//2, cap_height-60]
    pygame.mixer.init()

    try:
        with open(preferences_path, "r") as f:
            load_preferences = json.load(f)
            
            try:
                high_score = load_preferences["default.hdlevel_high_score"]
            except:
                high_score = 0
    except:
        load_preferences = {
            "hit_tolerance" : 50,
            "hit_interval" : 30,
            "no_camera" : True,
            "default.hdlevel_high_score" : 0
        }
    
    hit_tolerance = load_preferences["hit_tolerance"]
    hit_interval = load_preferences["hit_interval"]
    no_camera = load_preferences["no_camera"]
    
    
    user_text = ''
    submit_text = None
    submit_count = 0
    aura_time = 0

    points = 0
    combo = 0
    
    target_times = deque()
    target_coords = deque()
    try:
        level_name = "default.hdlevel"
        with open(levels_path + level_name, "r") as f:
            load_recording = json.load(f)
            song_name = load_recording["songname"]
            recorded_coords = deque(load_recording["coords"])
            recorded_times = deque(load_recording["times"])
            pygame.mixer.music.load(songs_path + song_name)
    except:
        recorded_coords = deque()
        recorded_times = deque()
        song_name = default_song_name
        level_name = ""
        pygame.mixer.music.load(songs_path + song_name)
    song_length = int(pygame.mixer.Sound(songs_path + song_name).get_length())
    song_length = datetime.time(minute=(song_length//60), second=(song_length%60)).strftime("%M:%S")
    show_target = False
    show_start_screen = True
    show_end_screen = False
    is_recording = False
    recording_mode = False
    two_handed_mode = False
    key_frame_mode = False
    playback_mode = True
    play_end_sound = True
    input_mode = False
    settings_mode = False
    written_end = False

    # Camera preparation ###############################################################
    cap = cv.VideoCapture(0, cv.CAP_DSHOW)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    # Model load #############################################################
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    while running:
        # Camera capture #####################################################
        ret, image = cap.read()
        if not ret:
            break
        image = cv.resize(image, (cap_width, cap_height))
        image = cv.flip(image, 1)  # Mirror display
        debug_image = copy.deepcopy(image)

        # remove camera feed if in settings
        if no_camera or input_mode:
            debug_image[:] = (0, 0, 0)

        if input_mode:
            debug_image = draw_message(debug_image, "Press [enter] to submit", (600, cap_height-30))

        # Detection implementation #############################################################
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True
        
        key = 0

        # reset typed text
        if input_mode:
            submit_text = None
        else:
            user_text = ''

        # process key input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if input_mode:
                    if event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        submit_text = user_text
                        submit_count += 1
                        input_mode = False
                    elif ((event.key >= pygame.K_a and event.key <= pygame.K_z) or (event.key >= pygame.K_0 and event.key <= pygame.K_9)
                                or event.key == pygame.K_MINUS or event.key == pygame.K_PERIOD or event.key == pygame.K_UNDERSCORE):
                        user_text += event.unicode
                else:
                    key = event.key
        
        # exit on escape
        if key == pygame.K_ESCAPE:  # ESC
            break

        # resets important variables - keeps level the same
        if key == pygame.K_r: # r to restart
            pygame.mixer.music.stop()
            pygame.mixer.Sound(sfx_path + "applause.wav").stop()
            # convoluted way to load recorded targets so that levels can be immediately played several times after recorded
            if recording_mode or key_frame_mode:
                load_recording["coords"] = list(recorded_coords)
                load_recording["times"] = list(recorded_times)
            recorded_coords = deque(load_recording["coords"])
            recorded_times = deque(load_recording["times"])
            user_text = ''
            submit_text = None
            submit_count = 0
            aura_time = 0
            points = 0
            combo = 0
            target_times = deque()
            target_coords = deque()
            show_target = False
            show_start_screen = True
            show_end_screen = False
            is_recording = False
            recording_mode = False
            two_handed_mode = False
            key_frame_mode = False
            playback_mode = True
            play_end_sound = True
            input_mode = False
            settings_mode = False
            written_end = False
        
        # enter settings mode
        if key == pygame.K_z and show_start_screen and not recording_mode: # z, change settings
            show_start_screen = False
            settings_mode = True
            input_mode = True

        # draw settings mode
        if settings_mode:
            debug_image = draw_message(debug_image, "CURRENT SETTINGS")
            debug_image = draw_message(debug_image, "Number of frames target appears - " + str(hit_interval), (10, 150))
            debug_image = draw_message(debug_image, "Distance to hit target - " + str(hit_tolerance), (10, 180))
            debug_image = draw_message(debug_image, "Show Camera - " + ("OFF" if no_camera else "ON"), (10, 210))
            if submit_count == 0:
                debug_image = draw_message(debug_image, "Enter # frames target appears (or nothing to keep current):", (10, 250))
            elif submit_count == 1:
                debug_image = draw_message(debug_image, "Enter distance to hit target (or nothing to keep current):", (10, 250))
                if not input_mode:
                    user_text = ''
                    try:
                        temp_input = int(submit_text)
                        hit_interval = temp_input
                    except:
                        print("using default")
                    input_mode = True
            elif submit_count == 2:
                debug_image = draw_message(debug_image, "Toggle camera mode? [y/(N)]:", (10, 250))
                if not input_mode:
                    user_text = ''
                    try:
                        temp_input = int(submit_text)
                        hit_tolerance = temp_input
                    except:
                        print("using default")
                    input_mode = True
            elif submit_count == 3:
                if not input_mode:
                    if submit_text == "y":
                        no_camera = not no_camera
                
                preferences_save = load_preferences
                preferences_save["hit_interval"] = hit_interval
                preferences_save["hit_tolerance"] = hit_tolerance
                preferences_save["no_camera"] = no_camera

                try:
                    with open(preferences_path, "w") as json_file:
                        json.dump(preferences_save, json_file)
                except Exception:
                    print("unable to write to preferences")

                submit_count = 0
                show_start_screen = True
                settings_mode = False

        if (key == pygame.K_q or key == pygame.K_w) and show_start_screen: # q or w, recording mode
            print("entering recording mode")
            if key == pygame.K_w: # w for two-handed
                print("two-handed mode")
                two_handed_mode = True
            #print("enter song file name: ")
            input_mode = True
            recorded_coords = deque()
            recorded_times = deque()
            recording_mode = True
            playback_mode = False
            show_start_screen = False

        if recording_mode and input_mode:
            if submit_count == 0:
                debug_image = draw_message(debug_image, "Enter song file name: ")
            elif submit_count == 1:
                debug_image = draw_message(debug_image, "Enter level name (without extension): ")

        if recording_mode and submit_count > 0 and not input_mode:
            if submit_count == 1:
                user_text = ''
                try:
                    song_name = submit_text
                    pygame.mixer.music.unload()
                    pygame.mixer.music.load(songs_path + song_name)
                    input_mode = True
                except Exception:
                    print("using default song and name user_default.hdlevel")
                    song_name = default_song_name
                    pygame.mixer.music.load(songs_path + song_name)
                    level_name = "user_default.hdlevel"
                    show_start_screen = True
                    submit_count = 0
                song_length = int(pygame.mixer.Sound(songs_path + song_name).get_length())
                song_length = datetime.time(minute=(song_length//60), second=(song_length%60)).strftime("%M:%S")
            if submit_count == 2:
                level_name = submit_text + '.hdlevel'
                show_start_screen = True
                submit_count = 0

        if key == pygame.K_s and playback_mode: # s to change level
            show_start_screen = False
            input_mode = True
        
        if playback_mode and submit_count == 0 and input_mode and not settings_mode:
            debug_image = draw_message(debug_image, "Enter level name (without extension): ")

        if playback_mode and submit_count == 1 and not input_mode and not settings_mode:
            try:
                level_name = submit_text + ".hdlevel"
                with open(levels_path + level_name, "r") as f:
                    load_recording = json.load(f)
                    song_name = load_recording["songname"]
                    recorded_coords = deque(load_recording["coords"])
                    recorded_times = deque(load_recording["times"])
                    pygame.mixer.music.load(songs_path + song_name)
                    try:
                        high_score = load_preferences[level_name + "_high_score"]
                    except:
                        high_score = 0
            except Exception:
                print("using default")
                try:
                    level_name = "default.hdlevel"
                    with open(levels_path + level_name, "r") as f:
                        load_recording = json.load(f)
                        song_name = load_recording["songname"]
                        recorded_coords = deque(load_recording["coords"])
                        recorded_times = deque(load_recording["times"])
                        pygame.mixer.music.load(songs_path + song_name)
                except IOError:
                    recorded_coords = deque()
                    recorded_times = deque()
                    song_name = default_song_name
                    level_name = ""
                    pygame.mixer.music.load(songs_path + song_name)
            song_length = int(pygame.mixer.Sound(songs_path + song_name).get_length())
            song_length = datetime.time(minute=(song_length//60), second=(song_length%60)).strftime("%M:%S")
            show_start_screen = True
            submit_count = 0
            
        if key == pygame.K_e and show_start_screen: # e, key frame mode after one-handed
            print("entering key frame mode")
            key_frame_mode = True
            key_frame_times = []
            key_frame_coords = []
        
        if key_frame_mode:
            debug_image = draw_mode(debug_image, "KEYFRAME MODE")
        if recording_mode:
            mode_desc = "RECORD MODE"
            if two_handed_mode:
                mode_desc += ":TWO HANDS"
            else:
                mode_desc += ":ONE HAND"
            if is_recording:
                mode_desc += ":RECORDING"
            debug_image = draw_mode(debug_image, mode_desc)
        
        if key == pygame.K_a and key_frame_mode:
            pygame.mixer.Sound(sfx_path + "menu-selection-click.wav").play()
            aura_time = 10
            print("getting frame")
            if (len(recorded_times) > 0) and (len(recorded_coords) > 0):
                key_frame_times.append(recorded_times[0])
                key_frame_coords.append(recorded_coords[0])

        coordmatch_count = 0
        coordmatch_goal = 4
        left_hand = []
        right_hand = []

        #  ####################################################################
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                handedness = handedness.classification[0].label[0:]
                # Landmark calculation
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                if (math.dist(landmark_list[8], start_coords) < hit_tolerance) and show_start_screen:
                    pygame.mixer.music.play()
                    show_start_screen = False
                    if recording_mode:
                        is_recording = True
                    else:
                        show_target = True
                        temp_hit_interval = hit_interval
                        if recorded_times[-1] == -1:
                            print("setting fluid hit_interval")
                            hit_interval = 2
                    
                if (handedness == "Right"):
                    right_hand = landmark_list
                elif (handedness == "Left"):
                    left_hand = landmark_list

                # Drawing part
                debug_image = draw_landmarks(debug_image, landmark_list, 1.0, (255, 255, 255))

        if show_target and (not key_frame_mode) and len(target_coords) > 0 and len(right_hand) > 0:
            if len(target_coords[0]) == 2:
                if len(left_hand) > 0:
                    coordmatch_goal = 8
                    current_finger = 4
                    while (current_finger <= 20):
                        if (math.dist(left_hand[current_finger], target_coords[0][0][current_finger]) < hit_tolerance):
                            coordmatch_count += 1
                        current_finger += 4
                    current_finger = 4
                    while (current_finger <= 20):
                        if (math.dist(right_hand[current_finger], target_coords[0][1][current_finger]) < hit_tolerance):
                            coordmatch_count += 1
                        current_finger += 4
            else:
                current_finger = 4
                while (current_finger <= 20):
                    if (math.dist(right_hand[current_finger], target_coords[0][current_finger]) < hit_tolerance):
                        coordmatch_count += 1
                    current_finger += 4
            
            
            if coordmatch_count >= coordmatch_goal:
                pygame.mixer.Sound(sfx_path + "menu-selection-click.wav").play()
                aura_time = 10
                multiplier = min(combo + 1, 10)
                points += (100 * multiplier)
                combo += 1
                # target_times[0] = 0
                target_coords.popleft()
                target_times.popleft()
            

        if (key == pygame.K_a or two_handed_mode) and is_recording and (len(right_hand) > 0): # a, record keyframe
            if not two_handed_mode or len(left_hand):
                recorded_times.append(pygame.mixer.music.get_pos())
                if two_handed_mode:
                    recorded_coords.append([left_hand, right_hand])
                else:
                    pygame.mixer.Sound(sfx_path + "menu-selection-click.wav").play()
                    recorded_coords.append(right_hand)

        if pygame.mixer.music.get_busy():
            song_pos = pygame.mixer.music.get_pos()
            if playback_mode:
                if len(recorded_times) > 0:
                    if recorded_times[0] < int(song_pos):
                        target_coords.append(recorded_coords[0])
                        target_times.append(hit_interval)
                        recorded_coords.popleft()
                        recorded_times.popleft()

            song_pos = song_pos // 1000
        else:
            song_pos = 0
            if not show_start_screen and (is_recording or show_target):
                if hit_interval == 2:
                    print("unsetting fluid hit interval")
                    hit_interval = temp_hit_interval
                show_end_screen = True
                is_recording = False
                show_target = False

        if show_start_screen:
            debug_image = draw_button(debug_image, start_coords, "Start")
            debug_image = draw_message(debug_image, "Songs and levels can be added to in their respective folders in game files.", (10, 80))
            debug_image = draw_message(debug_image, "Press [r] to restart (keeps loaded level)", (10, 120))
            debug_image = draw_message(debug_image, "Press [s] to load different level", (10, 150))
            debug_image = draw_message(debug_image, "Press [z] to change settings", (10, 180))
            debug_image = draw_message(debug_image, "Recording: ", (10, 240))
            debug_image = draw_message(debug_image, "A level consists of a series of snapshots of movements.", (10, 270))
            debug_image = draw_message(debug_image, "Press [q] to record right hand (only records when [a] is pressed)", (10, 300))
            debug_image = draw_message(debug_image, "Press [w] to record both hands (constantly records)", (10, 330))
            debug_image = draw_message(debug_image, "After recording both hands, press [e] to replay movements", (10, 360))
            debug_image = draw_message(debug_image, "Press [a] to choose snapshot to add to level (during right hand or replay)", (10, 390))
            debug_image = draw_message(debug_image, "Touch circle below to begin.", (10, 420))

        if show_target:
            if aura_time > 0:
                aura_time -= 1
                debug_image = draw_aura(debug_image, (255, 255, 255), (aura_time / 10))

            
        if show_end_screen:
            debug_image = draw_message(debug_image, "Press [r] to restart (keeps loaded level)")
            if (recording_mode or key_frame_mode):
                if not written_end:
                    is_recording = False
                    written_end = True

                    if key_frame_mode:
                        recorded_coords = deque(key_frame_coords)
                        recorded_times = deque(key_frame_times)

                    recording_save = {
                    "songname" : song_name,
                    "coords" : list(recorded_coords),
                    "times" : list(recorded_times)
                    }
                    
                    try:
                        with open(levels_path + level_name, "w") as json_file:
                            json.dump(recording_save, json_file)
                    except Exception:
                        print("unable to write to level")

                    print("done writing")


            else:
                # show_target = False
                if play_end_sound:
                    pygame.mixer.Sound(sfx_path + "applause.wav").play()
                    if points > high_score:
                        high_score = points
                        preferences_save = load_preferences
                        preferences_save[(level_name + "_high_score")] = high_score
                        try:
                            with open(preferences_path, "w") as json_file:
                                json.dump(preferences_save, json_file)
                        except Exception:
                            print("unable to write high score to preferences")
                    play_end_sound = False
                draw_end(debug_image, points, high_score, [350, 370])
                
        if show_target and len(target_coords) > 0:
            for i, coords in enumerate(target_coords):
                if len(coords) == 2:
                    debug_image = draw_landmarks(debug_image, coords[0], (target_times[i] / hit_interval), (255, 255 - ((i * 25) % 250), 0))
                    debug_image = draw_landmarks(debug_image, coords[1], (target_times[i] / hit_interval), (255, 255 - ((i * 25) % 250), 0))
                else:
                    debug_image = draw_landmarks(debug_image, coords, (target_times[i] / hit_interval), (255, 0, 0))
                target_times[i] -= 1
            if target_times[0] < 0:
                combo = 0
                target_coords.popleft()
                target_times.popleft()
            
        song_pos = datetime.time(minute=(song_pos//60), second=(song_pos%60)).strftime("%M:%S")
        debug_image = draw_info(debug_image, points, combo, song_pos, song_length, show_target)
        debug_image = draw_input(debug_image, user_text)
        # Display #############################################################
        
        imp = pygame.image.frombuffer(debug_image.tobytes(), debug_image.shape[1::-1], "BGR")
        scrn = pygame.display.set_mode((cap_width, cap_height))
        scrn.blit(imp, (0,0))
        pygame.display.flip()
    
    cap.release()
    pygame.quit()

def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    # Keypoint
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        # landmark_z = landmark.z

        landmark_point.append([landmark_x, landmark_y])

    return landmark_point


def draw_landmarks(image, landmark_point, transparency, color):
    initial_image = image.copy()
    if len(landmark_point) > 0:
        finger = 1
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[finger]), color, 2)
        while (finger <= 17):
            for joint in range(3):
                cv.line(image, tuple(landmark_point[finger+joint]), tuple(landmark_point[finger+joint+1]), color, 2)
            cv.line(image, tuple(landmark_point[finger]), tuple(landmark_point[(finger+4)%21]), color, 2)
            finger += 4

    cv.addWeighted(initial_image, 1 - transparency, image, transparency, 0, initial_image)
    image = initial_image
    return image

def draw_info(image, points, combo, song_pos, song_length, show_points):
    cv.putText(image, song_pos + "/" + song_length, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv.LINE_AA)
    cv.putText(image, song_pos + "/" + song_length, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1, cv.LINE_AA)

    if show_points:
        cv.putText(image, "Points:" + (str) (points), (10, 60), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv.LINE_AA)
        cv.putText(image, "Points:" + (str) (points), (10, 60), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1, cv.LINE_AA)

        cv.putText(image, "Combo:" + (str) (combo), (10, 90), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv.LINE_AA)
        cv.putText(image, "Combo:" + (str) (combo), (10, 90), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1, cv.LINE_AA)
    
    return image

def  draw_input(image, text, coords=(10, 480)):
    cv.putText(image, text, coords, cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv.LINE_AA)
    cv.putText(image, text, coords, cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1, cv.LINE_AA)

    return image

def draw_mode(image, text):
    return draw_message(image, text, (10, 510))

def draw_message(image, text, coords=(10, 120)):
    cv.putText(image, text, coords, cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv.LINE_AA)
    cv.putText(image, text, coords, cv.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 1, cv.LINE_AA)

    return image

def draw_target(image, target_coords, transparency, number):
    if (transparency >= 0):
        initial_image = image.copy()
        cv.circle(image, tuple(target_coords), 10, (0,0,255), -1)
        cv.circle(image, tuple(target_coords), 10, (0,0,0), 1)
        cv.putText(image, str(number), (target_coords[0] - 5, target_coords[1] + 5), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv.LINE_AA)
        cv.addWeighted(initial_image, 1 - transparency, image, transparency, 0, initial_image)
        image = initial_image

    return image

def draw_button(image, coords, label):
    offset = len(label) * 20
    cv.putText(image, label, (coords[0] - offset, coords[1] + 10), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv.LINE_AA)
    cv.putText(image, label, (coords[0] - offset, coords[1] + 10), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1, cv.LINE_AA)
    cv.circle(image, tuple(coords), 5, (255, 255, 255), 2)

    return image

def draw_aura(image, color, transparency):
    thickness = 5
    if (transparency >= 0):
        initial_image = image.copy()
        cv.rectangle(image, (0,0), (thickness, image.shape[0]), color, -1)
        cv.rectangle(image, (0,0), (image.shape[1], thickness), color, -1)
        cv.rectangle(image, (0, image.shape[0] - thickness), (image.shape[1], image.shape[0]), color, -1)
        cv.rectangle(image, (image.shape[1] - thickness,0), (image.shape[1], image.shape[0]), color, -1)
        cv.addWeighted(initial_image, 1 - transparency, image, transparency, 0, initial_image)
        image = initial_image

    return image

def draw_end(image, points, high_score, position):
    cv.putText(image, "Final Score: " + str(points), position, cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
    cv.putText(image, "Final Score: " + str(points), position, cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv.LINE_AA)
    cv.putText(image, "High Score: " + str(high_score), (position[0], position[1] + 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
    cv.putText(image, "High Score: " + str(high_score), (position[0], position[1] + 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv.LINE_AA)
    

    return image

if __name__ == '__main__':
    main()