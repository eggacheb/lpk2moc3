# lpk-to-moc3

 Based on [LPKUnpacker](https://github.com/ihopenot/LpkUnpacker)

## Extra functions

* Set up the model assets with *.moc3, *.model3.json,*.Physics3.json,*Pose3.json,"expressions","textures","sounds" and "motions" directories from .lpk file
* Recount the values of "CurveCount", "TotalPointCount" and "TotalSegmentCount" in *.motion3.json
* Link hit areas with motion group names

## Usage:
* Download lpk.exe from [releases](https://github.com/eggacheb/lpk2moc3/releases/download/1.0.1/lpk.exe)
* Create two new folders, output and lpkfolder
* Throw your lpk and config.json into the lpkfolder
* Open lpk.exe, then select your lpk and config.json, set the model name and output path to output, and make the model name shorter to avoid errors
