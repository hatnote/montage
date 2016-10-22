import main from './main/main';
import campaign from './campaign/campaign';
import dashboard from './dashboard/dashboard';
import round from './round/round';
import login from './login/login';
import voteEdit from './vote-edit/vote-edit';

import userList from './user-list';

export default () => {
  main();
  campaign();
  dashboard();
  round();
  login();
  voteEdit();

  userList();
};