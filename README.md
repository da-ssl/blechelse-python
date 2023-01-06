# Blechelse-Python
Blechelse-python is a Python script that uses a databse and the transport.rest-API to play the announcements of Deutsche Bahn _("Blechelse")_ automatically. In the future, it should also be possible to play announcements manually. For running this script, you need a folder of corresponding audio files and a database for these. 

## Code state
So far, the source code below represents only fragments and is not really operational. The app crashes quite often, because I'm just to lazy to handle Exceptions correctly. Please don't expect very clean code, I'm running this as a private project and have only little time to write and maintain the code. Additionally, I don't know Python very well now and am still in the learning process.

## Install
To run the script, you need to place the files of this repository in a subfolder of your audio files and install the packages listed in the ``requirements.txt`` file. To do so, run

    pip install -r requirements.txt

in your terminal. 