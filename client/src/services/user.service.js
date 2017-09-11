const Service = ($http, $q, $window) => {
  const admin = {};
  const juror = {};
  const user = {};

  const base = `${$window.__env.baseUrl}v1/`;

  function getAdmin() {
    return $http
      .get(base + 'admin')
      .then((data) => {
        angular.extend(admin, data);
        angular.extend(user, data.user);
        return data;
      });
  }

  function getJuror() {
    return $http
      .get(base + 'juror')
      .then((data) => {
        angular.extend(juror, data);
        angular.extend(user, data.user);
        return data;
      });
  }

  const service = {
    getAdmin,
    getJuror,
    getUser: () => $q.when(user),
    login: () => $http.get(window.__env.baseUrl + 'login'),
    logout: () => $http.get(window.__env.baseUrl + 'logout'),
  };

  return service;
};

export default Service;
