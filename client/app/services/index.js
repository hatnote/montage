import alertService from './alertService';
import dataService from './dataService';
import dialogService from './dialogService';
import userService from './userService';
import versionService from './versionService';

import filters from './filters';

export default () => {
  alertService();
  dataService();
  dialogService();
  userService();
  versionService();

  filters();
};
