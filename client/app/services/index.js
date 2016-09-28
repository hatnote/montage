import alertService from './alertService';
import dataService from './dataService';
import userService from './userService';
import versionService from './versionService';

export default () => {
  alertService();
  dataService();
  userService();
  versionService();
};
