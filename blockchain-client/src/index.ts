const express = require('express');
const handlebars = require('express-handlebars');
const path = require('path');
const bodyParser = require('body-parser');

const app = express();
const port = process.env.PORT;

const indexRouter = require('./routes/index.ts');
const smartContractRouter = require('./routes/smartcontracts.ts');

app.engine('handlebars', handlebars());
app.set('view engine', 'handlebars');

app.use(express.static(path.join(__dirname, "/public")));
app.use(bodyParser.urlencoded({extended: false}))
app.use(bodyParser.json())

app.use('/', indexRouter);
app.use('/smartcontracts', smartContractRouter);


app.listen(port, () => {
	console.log(`server started at http://localhost:${port}`)
})
