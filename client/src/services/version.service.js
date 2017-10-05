const VersionService = function($timeout, $mdTheming, themeProvider) {
  const service = {
    version: 'juror',
    getVersion: getVersion,
    setVersion: setVersion
  };

  return service;

  ////

  function getVersion() {
    return service.version;
  }

  function setVersion(version) {
      themeProvider.setDefaultTheme(version);
      service.version = version;
  }
};

export default VersionService;
