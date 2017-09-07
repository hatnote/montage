import alertService from './alert.service';
import dataService from './data.service';
import dialogService from './dialog.service';
import userService from './user.service';
import versionService from './version.service';

import filters from './filters';

export default () => {
  alertService();
  dataService();
  dialogService();
  userService();
  versionService();

  filters();
};
