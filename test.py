import cv2 as cv
import mediapipe as mp
import pbh.pbh as pbh
import numpy as np
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input


def getCroppedFace(image, maxX, maxY, minX, minY):
    face = image[minY:maxY, minX:maxX]
    face = cv.resize(face, (224, 224))
    # cv.imshow('face', face)
    face = img_to_array(face)
    face = preprocess_input(face)
    face = np.array([face], dtype='float32')
    return face


def getMask(on, off):
    if on > off:
        color = (0, 255, 0)
        maskFlag = True
        label = 'mask'
    else:
        color = (0, 0, 255)
        maskFlag = False
        label = 'no mask'

    label = '{} {:.2f}%'.format(
        label, max(on, off)*100)

    return label, color, maskFlag


def displayText(img, text, textPos, textThickness=1, textColor=(0, 255, 255), bgColor=(0, 0, 0), pad_x=6, pad_y=6):
    font = cv.FONT_HERSHEY_COMPLEX
    (t_w, t_h), _ = cv.getTextSize(text, font,
                                   1, textThickness)  # getting the text size
    x, y = textPos
    cv.rectangle(img, (x-pad_x, y + pad_y), (x+t_w+pad_x,
                 y-t_h-pad_y), bgColor, -1)  # draw rectangle
    cv.putText(img, text, textPos, font, 1,
               textColor, textThickness)  # draw in text

    return img


# class init
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_face_mesh = mp.solutions.face_mesh  # 얼굴

# True = video file
# False = web cam
isStaticVideo = False
output = False

# files
mediaPath = 'C:/Users/bv/python/hb-pbh-face-main (2)/hb-pbh-face-main/media'
# filePath = '{}/head/'.format(mediaPath)
# filePath = '{}/mask/'.format(mediaPath)
filePath = '{}/half/'.format(mediaPath)
# filePath = '{}/sample/'.format(mediaPath)
# filePath = '{}/error/'.format(mediaPath)
# filePath = '{}/video/'.format(mediaPath)
# filePath = '{}/'.format(mediaPath)
fileList = os.listdir(filePath)
fileName = '{}{}'.format(filePath, fileList[0])
fileName = f'{mediaPath}/13139-record_01-1-1676274453852-u6cc4syx0h.mp4'
if(isStaticVideo):
    cap = cv.VideoCapture(fileName)  # 파일
else:
    cap = cv.VideoCapture(0)  # 웹캠

# init
mask_detector = load_model('C:/Users/bv/python/hb-pbh-face-main (2)/hb-pbh-face-main/mask_detector.model')
CONN = [
    (193, 417),  # 얼굴
    (10, 152),  # 얼굴
    (234, 447),  # 얼굴
    (473, 445),  # 홍채
    (159, 145), (33, 133),  # 오른쪽눈
    (386, 374), (263, 362),  # 왼쪽눈
    (13, 14),
    # (78, 308)  # 입
]
videoTime = int(cap.get(cv.CAP_PROP_FRAME_COUNT))  # 동영상 총 프레임
fps = cap.get(cv.CAP_PROP_FPS)  # 초당 프레임
baseFrame = round(videoTime / 10)  # 총 프레임의 10%
availableFrame = 0  # 유효한 프레임 카운터 (얼굴 트레킹 되고 있는 프레임)

blinksCounter = 0  # 눈깜빡임
cefCounter = 0

baseLandmarks = []
baseFaceCenter = ''  # 얼굴움직임
sumFaceDistance = 0

baseEyesCenter = 0  # 눈움직임
sumEyesDistance = 0

sCount = 0

lvCounter = [0, 0, 0, 0, 0, 0]  # 입움직임 레벨
maskFlag = False  # 마스크 썼는지 안썼는지

success, image = cap.read()
cv.imshow('original', image)

if output:
    fourcc = cv.VideoWriter_fourcc(*'XVID')  # 동영상 저장
    out = cv.VideoWriter('en_videos/sample.mp4', fourcc, 30.0, (640, 480))

with mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh:
    while cap.isOpened():  # 카메라 켜져있음
        success, image = cap.read()
        if not success:
            print("종료")
            break  # 웹캠이면 continue 파일이면 break.

        cv.imshow('original', image)
        image = cv.resize(image, None, fx=1, fy=1, interpolation=cv.INTER_CUBIC)  # 동영상 사이즈 변경.
        image.flags.writeable = False  # 이미지 다시쓰기
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        cv.imshow('resize', image)

        resultsFace = face_mesh.process(image)

        # 이미지에 얼굴 메쉬 주석을 그립니다.
        image.flags.writeable = True
        image = cv.cvtColor(image, cv.COLOR_RGB2BGR)
        img_height, img_width = image.shape[:2]
        if resultsFace.multi_face_landmarks:  # 얼굴 트레킹 값 있음
            for face_landmarks in resultsFace.multi_face_landmarks:
                if(availableFrame == 0):
                    baseLandmarks = face_landmarks
                availableFrame += 1  # 유효한 프레임 카운트

                nowMesh2D = pbh.getMesh2D(
                    img_width, img_height, face_landmarks)
                nowMesh3D = pbh.getMesh3D(
                    img_width, img_height, face_landmarks)

                if not(availableFrame % 10):  # 마스크 체크
                    maxX, maxY, minX, minY=pbh.vertax(
                        img_width, img_height, nowMesh2D)
                    croppedFace=getCroppedFace(image, maxX, maxY, minX, minY)
                    (maskOn, maskOff)=mask_detector.predict(
                        croppedFace, batch_size=32)[0]

                    label, color, maskFlag=getMask(maskOn, maskOff)
                    cv.putText(image, label, (minX, maxY - 10),
                               cv.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                    cv.rectangle(image, (minX, maxY), (maxX, minY), color, 2)

                faceClass = pbh.Face(nowMesh3D)
                eyeClass = pbh.Eye(nowMesh2D)
                lipClass = pbh.Lip(nowMesh2D)

                faceCenter = faceClass.getFaceCenter3D()  # 얼굴 중앙좌표 3D
                eyesCenter = eyeClass.getIrisToEyeAvg()  # 눈

                if not(availableFrame % int(fps)):
                    sCount += 1
                    baseMesh2D = pbh.getMesh2D(
                        img_width, img_height, baseLandmarks)
                    baseMesh3D = pbh.getMesh3D(
                        img_width, img_height, baseLandmarks)
                    baseFaceClass = pbh.Face(baseMesh3D)  # 머리움직임 베이스
                    baseEyeClass = pbh.Eye(baseMesh2D)
                    baseFaceCenter = baseFaceClass.getFaceCenter3D()
                    baseEyesCenter = baseEyeClass.getIrisToEyeAvg()
                    sumFaceDistance += abs(pbh.Common.getEuclaideanDistance3D(
                        baseFaceCenter, faceCenter))
                    if not(blinkRatio > 5.5):
                        sumEyesDistance += abs(baseEyesCenter - eyesCenter)
                    baseLandmarks = face_landmarks

                displayText(image, 'time:{}'.format(
                    sCount), (0, 150))
                displayText(image, 'head:{}'.format(
                    sumFaceDistance), (0, img_height-10))

                displayText(image, 'eyes:{}'.format(
                    sumEyesDistance), (0, img_height-70))
                mp_drawing.draw_landmarks(  # 베이스 랜드마크 그림
                    image=image,
                    landmark_list=baseLandmarks,
                    connections=CONN,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing.DrawingSpec(thickness=1, circle_radius=1, color=(0, 0, 0)))
                # if(isStaticVideo):
                #     if(baseFrame > availableFrame):  # 유효한 프레임을 목표 프레임까지 수집
                #         for i in range(len(face_landmarks.landmark)):
                #             baseLandmarks.landmark[i].x += face_landmarks.landmark[i].x
                #             baseLandmarks.landmark[i].y += face_landmarks.landmark[i].y
                #             baseLandmarks.landmark[i].z += face_landmarks.landmark[i].z
                #     elif(baseFrame == availableFrame):  # 수집완료
                #         for i in range(len(baseLandmarks.landmark)):
                #             baseLandmarks.landmark[i].x=baseLandmarks.landmark[i].x / \
                #                 availableFrame
                #             baseLandmarks.landmark[i].y=baseLandmarks.landmark[i].y / \
                #                 availableFrame
                #             baseLandmarks.landmark[i].z=baseLandmarks.landmark[i].z / \
                #                 availableFrame
                #         baseMesh2D=pbh.getMesh2D(
                #             img_width, img_height, baseLandmarks)
                #         baseMesh3D=pbh.getMesh3D(
                #             img_width, img_height, baseLandmarks)

                #         baseFaceClass=pbh.Face(baseMesh3D)  # 머리움직임 베이스
                #         baseFaceCenter=baseFaceClass.getFaceCenter3D()

                #         baseEyeClass=pbh.Eye(baseMesh2D)
                #         baseEyesCenter=baseEyeClass.getIrisToEyeAvg()
                #     elif(baseFrame < availableFrame):  # 수집된 데이터와 비교
                #         sumFaceDistance += abs(pbh.Common.getEuclaideanDistance3D(
                #             baseFaceCenter, faceCenter))
                #         if not(blinkRatio > 5.5):
                #             sumEyesDistance += abs(baseEyesCenter - eyesCenter)

                #         displayText(image, 'head:{}'.format(
                #             sumFaceDistance), (0, img_height-10))

                #         displayText(image, 'eyes:{}'.format(
                #             sumEyesDistance), (0, img_height-70))

                blinkRatio = eyeClass.getBlinkRatio()  # 눈깜빡임
                if blinkRatio > 5.5:
                    cefCounter += 1
                else:
                    if cefCounter >= 2:
                        blinksCounter += 1
                        cefCounter = 0
                        # print('깜빡 {}회'.format(blinksCounter))

                displayText(image, 'blink:{}'.format(
                    blinksCounter), (0, 70))

                if not(maskFlag):
                    lipRatio = lipClass.getLipDistance()  # 입술 상,하 비율 좌,우 거리
                    lv = lipClass.getLipLv(lipRatio[1])
                    displayText(image, 'lip lv: {}'.format(lv), (0, 30))
                    lvCounter[lv] += 1

                if not isStaticVideo:
                    displayText(image, 'x:{}'.format(
                        faceCenter[0]), (0, img_height-130))
                    displayText(image, 'y:{}'.format(
                        faceCenter[1]), (0, img_height-90))
                    displayText(image, 'z:{}'.format(
                        faceCenter[2]), (0, img_height-50))
                    asd = eyesCenter
                    if blinkRatio > 5.5:
                        asd = 'close'
                    displayText(image, 'eyes:{}'.format(
                        asd), (0, img_height-10))
                mp_drawing.draw_landmarks(  # 베이스 랜드마크 그림
                    image=image,
                    landmark_list=face_landmarks,
                    connections=CONN,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing.DrawingSpec(thickness=1, circle_radius=1, color=(0, 255, 0)))
        if(output):
            out.write(image)
        cv.imshow('absolute', image)
        if cv.waitKey(5) & 0xFF == 27:
            break

time1 = videoTime / fps
# blinkPerS = round(blinksCounter / videoTime if blinksCounter else 0, 2)
print('시간:{}'.format(time1))
print('프레임:{}'.format(videoTime))
print('가용 프레임:{}'.format(availableFrame))
print('머리 움직임: {}'.format(sumFaceDistance))  # 머리움직임
print('시선처리: {}'.format(sumEyesDistance))  # 시선처리
for key, val in enumerate(lvCounter):
    print('입 움직임 lv{}: {}'.format(key, val))  # 입움직임

print('눈깜빡임: {}회'.format(blinksCounter))  # 눈깜삑임
# print("time :", time.time() - start)
cap.release()  # cap 해제
