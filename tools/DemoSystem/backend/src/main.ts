import 'express-async-errors'
import express, {Request, Response} from 'express';
import path from 'path';
import {errorHandler} from "./utils/tool";
import apiV1Router from './api/v1/main';


const frontendPath = path.resolve(__dirname, '../../frontend/dist/frontend');
const app = express();

app.use(express.json());
app.use(express.urlencoded({extended: true}));
app.use('/static', express.static(path.join(frontendPath)));
app.use('/api/v1', apiV1Router);
app.get('/pro/*', (req: Request, res: Response) => {
    res.sendFile(path.join(frontendPath, 'index.html'));
});
app.get('/', (req: Request, res: Response) => {
    res.redirect('/pro/home');
});
app.use(errorHandler)

app.listen(5050, '0.0.0.0');