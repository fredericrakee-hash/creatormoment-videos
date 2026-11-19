# usage: enc.sh in.mp4 audio.wav out.mp4 kbps
cd $(mktemp -d)
ffmpeg -y -loglevel error -i "$1" -c:v libx264 -preset medium -b:v ${4}k -pass 1 -an -f mp4 /dev/null
ffmpeg -y -loglevel error -i "$1" -i "$2" -c:v libx264 -preset medium -b:v ${4}k -maxrate $((${4}*2))k -bufsize $((${4}*4))k -pass 2 -pix_fmt yuv420p -c:a aac -b:a 160k -shortest -movflags +faststart "$3"
