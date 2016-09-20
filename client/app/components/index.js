import main from './main/main';
import campaign from './campaign/campaign';
import dashboard from './dashboard/dashboard';
import image from './image/image';
import round from './round/round';
import login from './login/login';

export default () => {
  main();
  campaign();
  dashboard();
  image();
  round();
  login();
};