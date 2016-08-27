import React from 'react';

const RoundImagesInfo = ({type, imagesCount, roundSource, categoriesSource, onImportFromCommons}) => {
    switch (type) {
        case 'uninitialized':
            return <div>
                <span>No images imported yet! </span>
                <button type="button" className="btn btn-default" name="import" onClick={onImportFromCommons}>
                    Import images from Commons
                </button>
            </div>
        case 'from-round':
            return <div>
                {imagesCount} images imported from round {roundSource}
            </div>
        case 'from-categories':
            let categories = categoriesSource.map(
                (cat) => <a href={"https://commons.wikimedia.org/wiki/Category:" + cat}>{cat} </a>)
            return <div>
                {imagesCount} images imported from Commons Categories: {categories}
            </div>
        default:
            return null; // This shouldn't really happen
    }
};

RoundImagesInfo.defaultProps = {
    type: 'uninitialized',
}

RoundImagesInfo.propTypes = {
    type: React.PropTypes.oneOf(['uninitialized', 'from-round', 'from-categories'])
}

export default RoundImagesInfo;
