/*** @jsx React.DOM */
var joinClasses = require("react/lib/joinClasses");
var classSet = require("react/lib/cx");
var React = require("react");

var LoadingIndicator = React.createClass({
  propTypes: {
    message: React.PropTypes.string,
    mini:  React.PropTypes.bool
  },

  getDefaultProps() {
    return {
      message: "Loading..."
    };
  },

  render() {
    var className = classSet({
      "loading": true,
      "mini": this.props.mini,
    });

    return (
      <div className={joinClasses(this.props.className, className)}>
        {this.props.message}
      </div>
    );
  }
});

module.exports = LoadingIndicator;
