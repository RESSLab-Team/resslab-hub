# resslab-hub

## Project setup

```
npm install
```

### Compiles and hot-reloads for development

```
npm run serve
```

### Compiles and minifies for production

```
npm run build
```

### Run your unit tests

```
npm run test:unit
```

### Lints and fixes files

```
npm run lint
```

### Customize configuration

See [Configuration Reference](https://cli.vuejs.org/config/).

## Video Optimization

```bash
# Crop video if necessary
ffmpeg -i input.mp4 -filter:v "crop=1620:1080:150:0" -y cropped.mp4

# Optimize video
ffmpeg -y -i cropped.mp4 -c:v libx264 -b:v 2500k -profile:v high -pix_fmt yuv420p -color_primaries 1 -color_trc 1 -colorspace 1 -movflags +faststart -an output.mp4
```
