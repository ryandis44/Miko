from PIL import Image, ImageOps
import re
import pytesseract

def get_best_position():
    try:
        pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
        im = ImageOps.grayscale(Image.open('images/card.png'))
        w, h = im.size
        im = ImageOps.invert(im)
        l_count, l_ed = get_ed_and_count(im, 157, 370, w - 882, h - 35)
        ml_count, ml_ed = get_ed_and_count(im, 430, 370, w - 617, h - 35)
        mr_count, mr_ed = get_ed_and_count(im, 700, 370, w - 338, h - 35)
        r_count, r_ed = get_ed_and_count(im, 980, 370, w - 63, h - 35)
        
        eds = [l_ed, ml_ed, mr_ed, r_ed]
        counts = [l_count, ml_count, mr_count, r_count]
        
        for i, count in enumerate(counts):
            if count == 1:
                continue
            if count < 100:
                return i, 4

        if max(eds) == 1:
            return counts.index(min(counts)), max(eds)

        return eds.index(max(eds)), max(eds)
    except:
        return 0, 0


def get_ed_and_count(im, left, top, right, bottom):
    try:
        new_im = im.crop((left, top, right, bottom))
        # new_im.show()
        text = pytesseract.image_to_string(new_im)
        # print(text)
        if text == "":
            for i in range(1, 10):
                new_im = im.crop((left+i, top, right-i, bottom))
                text = pytesseract.image_to_string(new_im)
                if text != "":
                    break
        try:
            count, ed = text.split('-', 1)
        except:
            return 1, 1
        count = re.findall(r'\d+', count)
        count = int(count[0])
        ed = ed.strip()
        if(ed[0].isdigit()):
            ed = int(ed[0])
        else:
            ed = 1
        # print(type(ed))
        # print(f"Count: {count} Ed: {ed}")
        return count, ed
    except:
        return 1, 1

# get_best_position()