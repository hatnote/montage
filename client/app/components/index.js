import main from './main/main';
import campaign from './campaign/campaign';
import dashboard from './dashboard/dashboard';
import round from './round/round';
import login from './login/login';

export default () => {
  main();
  campaign();
  dashboard();
  round();
  login();
};