import json
import os
import re
import subprocess
from tkinter import Text, NORMAL, DISABLED, END

import motion_spec


LogArea: Text | None = None


def rmdir(path):
    for i in os.listdir(path):
        p = os.path.join(path, i)
        if os.path.isdir(p):
            rmdir(p)
        else:
            os.remove(p)
    os.rmdir(path)


def Log(info):
    global LogArea
    LogArea.config(state=NORMAL)
    LogArea.insert(END, info + "\n")
    LogArea.see(END)
    LogArea.config(state=DISABLED)


def CheckPath(model_dir: str):
    global motionPath, expressionPath, texturePath, soundPath
    motionPath = os.path.join(model_dir, "motions")
    expressionPath = os.path.join(model_dir, "expressions")
    texturePath = os.path.join(model_dir, "textures")
    soundPath = os.path.join(model_dir, "sounds")
    if not os.path.exists(motionPath):
        os.makedirs(motionPath)
    if not os.path.exists(expressionPath):
        os.makedirs(expressionPath)
    if not os.path.exists(texturePath):
        os.makedirs(texturePath)
    if not os.path.exists(soundPath):
        os.makedirs(soundPath)
    return motionPath, expressionPath, texturePath, soundPath


def ProcessExpressions(expressions, model_dir, expressionPath, modelName):
    for expression in expressions:
        _File = expression.get("File", None)
        if _File:
            srcPath = os.path.join(model_dir, _File)
            if not os.path.exists(srcPath):
                Log("File not found: %s" % srcPath)
                continue
            fileName = _File.replace("FileReferences_Expressions", modelName).replace("_File_0", "").replace(".json", ".exp3.json")
            targetPath = os.path.join(expressionPath, fileName)
            relativePath = os.path.relpath(targetPath, model_dir)
            try:
                os.rename(srcPath, targetPath)
                Log("Moved and renamed %s to %s" % (srcPath, targetPath))
                expression["File"] = relativePath.replace("\\", "/")
            except FileNotFoundError as e:
                Log("Error moving %s to %s: %s" % (srcPath, targetPath, str(e)))


def update_nested_references(data, old_name, new_name):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and value == old_name:
                data[key] = new_name
            else:
                update_nested_references(value, old_name, new_name)
    elif isinstance(data, list):
        for item in data:
            update_nested_references(item, old_name, new_name)


def SetupModel(model_dir: str, modelNameBase: str = None):
    motionPath, expressionPath, texturePath, soundPath = CheckPath(model_dir)
    if not modelNameBase:
        modelNameBase = os.path.split(model_dir)[-1]
    modelJsonPathList = []
    pat = re.compile("^model\\d?.json$")
    for groupName in os.listdir(model_dir):
        if pat.findall(groupName):
            modelJsonPathList.append(os.path.join(model_dir, groupName))

    Log("Model Json Found: %s" % modelJsonPathList)
    removeList = []
    for idx, modelJsonPath in enumerate(modelJsonPathList):
        modelName = modelNameBase if idx == 0 else modelNameBase + str(idx + 1)
        with open(modelJsonPath, 'r', encoding='utf-8') as f:
            model_data = json.load(f)

        ProcessExpressions(model_data["FileReferences"].get("Expressions", []), model_dir, expressionPath, modelName)

        motions = model_data["FileReferences"].get("Motions", [])
        for groupName in motions:
            Log("[Motion Group]: %s" % groupName)
            for motion in motions[groupName]:
                _File = motion.get("File", None)
                if _File:
                    srcPath = os.path.join(model_dir, _File)
                    fileName = _File.replace("FileReferences_Motions", modelName).replace("_File_0", "").replace(".json", ".motion3.json")
                    targetPath = os.path.join(motionPath, fileName)
                    with open(srcPath, 'r', encoding='utf-8') as src_file:
                        src = json.load(src_file)
                        Log("CurveCount: %d" % src["Meta"]["CurveCount"])
                        Log("TotalSegmentCount: %d" % src["Meta"]["TotalSegmentCount"])
                        Log("TotalPointCount: %d" % src["Meta"]["TotalPointCount"])
                        with open(targetPath, 'w', encoding='utf-8') as tgt_file:
                            curve_count, segment_count, point_count = motion_spec.recount_motion(src)
                            Log("%d, %d, %d" % (curve_count, segment_count, point_count))
                            src["Meta"]["CurveCount"] = curve_count
                            src["Meta"]["TotalSegmentCount"] = segment_count
                            src["Meta"]["TotalPointCount"] = point_count
                            json.dump(src, tgt_file, ensure_ascii=False, indent=2)
                    removeList.append(srcPath)
                    Log("[Motion]: %s >>> %s" % (_File, targetPath))
                    motion["File"] = "motions/" + fileName

                # Move related sound files to sounds directory
                soundFile = motion.get("Sound", None)
                if soundFile and re.search(r"^FileReferences_Motions_([^_]+_)*Sound_\d+\.(mp3|wav)$", soundFile, re.IGNORECASE):
                    srcPath = os.path.join(model_dir, soundFile)
                    fileName = soundFile.replace("FileReferences_Motions_", "").replace("_Sound_", "_").replace(".mp3", ".mp3").replace(".wav", ".wav")
                    targetPath = os.path.join(soundPath, fileName)
                    try:
                        os.rename(srcPath, targetPath)
                        Log("Moved and renamed %s to %s" % (srcPath, targetPath))
                        motion["Sound"] = "sounds/" + fileName
                        # Update nested references
                        update_nested_references(model_data, soundFile, "sounds/" + fileName)
                    except FileNotFoundError as e:
                        Log("Error moving %s to %s: %s" % (srcPath, targetPath, str(e)))

        # Move FileReferences_Textures_0_0.png to textures directory
        textures = model_data["FileReferences"].get("Textures", [])
        for idx, texture in enumerate(textures):
            if isinstance(texture, str) and texture.endswith(".png"):
                srcPath = os.path.join(model_dir, texture)
                fileName = texture.replace("FileReferences_Textures_", "").replace(".png", ".png")
                targetPath = os.path.join(texturePath, fileName)
                try:
                    os.rename(srcPath, targetPath)
                    Log("Moved and renamed %s to %s" % (srcPath, targetPath))
                    textures[idx] = "textures/" + fileName
                except FileNotFoundError as e:
                    Log("Error moving %s to %s: %s" % (srcPath, targetPath, str(e)))

        # Rename FileReferences_Physics_0.json to madoka.Physics3.json
        physicsFile = model_data["FileReferences"].get("Physics", None)
        if physicsFile and physicsFile.endswith("_0.json"):
            srcPath = os.path.join(model_dir, physicsFile)
            fileName = modelName + ".Physics3.json"
            targetPath = os.path.join(model_dir, fileName)
            try:
                os.rename(srcPath, targetPath)
                Log("Moved and renamed %s to %s" % (srcPath, targetPath))
                model_data["FileReferences"]["Physics"] = fileName
                # Update nested references
                update_nested_references(model_data, physicsFile, fileName)
            except FileNotFoundError as e:
                Log("Error moving %s to %s: %s" % (srcPath, targetPath, str(e)))

        # Rename FileReferences_Pose_0.json to madoka.Pose3.json
        poseFile = model_data["FileReferences"].get("Pose", None)
        if poseFile and poseFile.endswith("_0.json"):
            srcPath = os.path.join(model_dir, poseFile)
            fileName = modelName + ".Pose3.json"
            targetPath = os.path.join(model_dir, fileName)
            try:
                os.rename(srcPath, targetPath)
                Log("Moved and renamed %s to %s" % (srcPath, targetPath))
                model_data["FileReferences"]["Pose"] = fileName
                # Update nested references
                update_nested_references(model_data, poseFile, fileName)
            except FileNotFoundError as e:
                Log("Error moving %s to %s: %s" % (srcPath, targetPath, str(e)))

        # Rename FileReferences_Moc_0.moc3 to madoka.moc3
        mocFile = model_data["FileReferences"].get("Moc", None)
        if mocFile and mocFile.endswith("_0.moc3"):
            srcPath = os.path.join(model_dir, mocFile)
            fileName = modelName + ".moc3"
            targetPath = os.path.join(model_dir, fileName)
            try:
                os.rename(srcPath, targetPath)
                Log("Moved and renamed %s to %s" % (srcPath, targetPath))
                model_data["FileReferences"]["Moc"] = fileName
                # Update nested references
                update_nested_references(model_data, mocFile, fileName)
            except FileNotFoundError as e:
                Log("Error moving %s to %s: %s" % (srcPath, targetPath, str(e)))

        for idx, hitArea in enumerate(model_data.get("HitAreas", [])):
            if hitArea.get("Motion", None) is not None:
                model_data["HitAreas"][idx]["Name"] = hitArea["Motion"].split(":")[0]

        if model_data.get("Controllers", None) is not None:
            if model_data["Controllers"].get("ParamHit", None) is not None:
                if model_data["Controllers"]["ParamHit"].get("Items", None) is not None:
                    for item in model_data["Controllers"]["ParamHit"]["Items"]:
                        if item.get("EndMtn", None) is not None:
                            model_data["HitAreas"].append(
                                {
                                    "Name": item.get("EndMtn"),
                                    "Id": item.get("Id")
                                }
                            )

        with open(os.path.join(model_dir, modelName + ".model3.json"), "w", encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)

        if os.path.exists(modelJsonPath):
            os.remove(modelJsonPath)
        for i in set(removeList):
            Log("removing: %s" % i)
            if os.path.exists(i) and i not in model_data.get("Pose", ""):
                os.remove(i)
        new_dir = os.path.join(os.path.split(model_dir)[0], modelName)
        if os.path.exists(new_dir):
            rmdir(new_dir)
        os.rename(model_dir, new_dir)


if __name__ == '__main__':
    SetupModel("path to model dir", "model name")
