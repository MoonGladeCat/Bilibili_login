'''
crack the reCaptcha of Bilibili
div class: gt_bg gt_show
div class: gt_fullbg gt_show
tagBg = bsObj.find('div', {'class':'gt_cut_bg gt_show'})
tagBgFull = bsObj.find('div', {'class':'gt_cut_fullbg gt_show'})
slices = tagBg.find_all('div', {'class':'gt_cut_bg_slice'})
'''
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from urllib.request import urlretrieve

from bs4 import BeautifulSoup
from PIL import Image
from io import StringIO
import os
import requests
import time
import re
import random


def inputInfor(driver, username, password):
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-username")))
    element.send_keys(username)
    time.sleep(1)
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-passwd")))
    element.send_keys(password)
    time.sleep(1)


def getImageUrl(styleString):
    return (re.findall("url\(\"(.*)\"\)",styleString))[0]

def getImageName(imageUrl):
    return (os.path.split(imageUrl))[1]

def retrieveImage(imageUrl):
    #print('retrieving image: ' + imageUrl)
    imageName = getImageName(imageUrl)
    urlretrieve(imageUrl, imageName)

def getImageSlicePartition(styleString):
    partition = re.findall("background-position: (.*)px (.*)px", styleString)
    positionX = int(partition[0][0])
    positionY = int(partition[0][1])
    return (positionX, positionY)

def getBoxByPartition(partitionList, pixelX, pixelY):
    boxList = []
    for partition in partitionList:
        positionX = abs(partition[0])
        positionY = abs(partition[1])
        left  = positionX - 1
        right = left + pixelX
        upper = positionY
        if positionY == pixelY:
            lower = positionY + pixelY
        else:
            lower = pixelY
        box = (left, upper, right, lower)
        boxList.append(box)
    return boxList

def getBoxByID(row, coloum, pixelX, pixelY):
    boxList = []
    for r in list(range(0, row)):
        for c in list(range(0, coloum)):
            left  = c * pixelX
            right = left + pixelX
            upper = pixelY * r
            lower = upper + pixelY
            box = (left, upper, right, lower)
            boxList.append(box)
    return boxList  

def mergeImage(partitionList, imageUrl):
    retrieveImage(imageUrl)
    imageName = getImageName(imageUrl)
    imageOrigin = Image.open(imageName).convert('RGB')
    imageMerged = Image.new('RGB', imageOrigin.size) 
    blocks = len(partitionList)
    row    = 2
    coloum = int(blocks / row)
    pixelX  = int((imageOrigin.size)[0] / coloum)
    pixelY  = int((imageOrigin.size)[1] / row)
    paritionBoxList = getBoxByPartition(partitionList, pixelX, pixelY)
    idBoxList       = getBoxByID(row, coloum, pixelX, pixelY)
    for block in list(range(0, blocks)):
        part =imageOrigin.crop(paritionBoxList[block])
        imageMerged.paste(part, idBoxList[block])

    imageResized = imageMerged.resize((260, 116))
    imageOrigin.close()
    os.remove(imageName)
    return imageResized

def getMergedImage(bsObj, bgName, sliceName):
    partitionList = []
    tagBg = bsObj.find('div', {'class':bgName})
    tagSlices = tagBg.find_all('div', {'class':sliceName})
    for tag in tagSlices:
        styleString = tag.attrs['style']
        imageUrl = getImageUrl(styleString)
        partition = getImageSlicePartition(styleString)
        partitionList.append(partition)
        
    return mergeImage(partitionList, imageUrl)

def getMoveDistance(imageCut, imageFull):
    xSize, ySize = imageFull.size
    pxCut  = imageCut.load()
    pxFull = imageFull.load()
    startPx = xSize - 1
    endPx   = 0
    for y in list(range(0, ySize - 1)):
        for x in list(range(0,xSize - 1)):
            r = abs(pxFull[x, y][0] - pxCut[x, y][0])
            g = abs(pxFull[x, y][1] - pxCut[x, y][1])
            b = abs(pxFull[x, y][2] - pxCut[x, y][2])
            grey = int((r + g  + b) / 3)
            if grey > 50:
                if x < startPx:
                    startPx = x
                if x > endPx:
                    endPx   = x
    return startPx, endPx

def getMoveTrack(distance):
    trackList = []
    mid = (distance * 2) / 3
    t = 0.2
    v = 0
    dis = 0
    
    while dis < distance:
        if dis < mid:
            a = 3
        else:
            a = -2        
        v0 = v
        v  = v0 + a * t
        move = v0 * t + a * t * t / 2
        dis  += move
        trackList.append(round(move))
    return trackList

def getSlider(driver):
    while True:
        try:
            slider = driver.find_element_by_xpath("//*[@class='gt_slider_knob gt_show']")
            break
        except:
            time.sleep(0.5)
        
    return slider

def moveSlider(driver):
    bsObj = BeautifulSoup(driver.page_source, 'html.parser')
    imageCut  = getMergedImage(bsObj, 'gt_cut_bg gt_show', 'gt_cut_bg_slice')
    imageFull = getMergedImage(bsObj, 'gt_cut_fullbg gt_show', 'gt_cut_fullbg_slice')
    start, end = getMoveDistance(imageCut, imageFull)
    track  = getMoveTrack(start - 5)
    slider = getSlider(driver)
    ActionChains(driver).click_and_hold(slider).perform()
    while track:
        x = random.choice(track)
        ActionChains(driver).move_by_offset(xoffset=x, yoffset=0).perform()
        track.remove(x)
        time.sleep(0.1)
    ActionChains(driver).release().perform()

def openBrowser(url, headless):
    if headless == True:
        options = webdriver.FirefoxOptions()
        options.set_headless()
        options.add_argument('--disable-gpu')
        driver = webdriver.Firefox(firefox_options=options)
    else:
        driver = webdriver.Firefox()

    driver.get(url)

    return driver

def loginBili(usrname, password):
    url = 'https://passport.bilibili.com/login' 
    driver = openBrowser(url, False)
    inputInfor(driver, usrname, password)
    moveSlider(driver)
    time.sleep(5)
    driver.quit()

if __name__ == '__main__':
    loginBili('usrname', 'password') 













