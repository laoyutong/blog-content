# useState
在输入`abc`后回车就会生成`const [abc, setAbc] = useState();`
```json
  "useState": {
    "prefix": "us",
    "body": ["const [$1, set${1/(.*)/${1:/capitalize}/}] = useState($2);"]
  }
```