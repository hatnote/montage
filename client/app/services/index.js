import dataService from './dataService';
import userService from './userService';
import versionService from './versionService';

export default () => {
  dataService();
  userService();
  versionService();
};
