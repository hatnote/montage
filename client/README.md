### montage front-end app

#### Install

In order to install front-end app, you need to run command below in `client` directory:

```
npm install
```

#### Run

For developer work, run command below. It will build app with watcher of changes in code. Then go to [localhost:5000/#/](http://localhost:5000/#/)

```
npm run start
```

#### Build

For one-time build run command below.

```
npm run build
```

For `dev ` and `prod` environment use code below. Variables like URL base, can be set in `index_*.ejs` [here](https://github.com/hatnote/montage/tree/master/client/app).

```
export NODE_ENV=dev
npm run build
```

```
export NODE_ENV=prod
npm run build
```

Note: on Windows instead of `export NODE_ENV` use `set NODE_ENV`.
