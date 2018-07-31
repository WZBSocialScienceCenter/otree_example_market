# Example implementation for an experiment with dynamically determined data quantity in oTree

July 2018, Markus Konrad <markus.konrad@wzb.eu> / [Berlin Social Science Center](https://wzb.eu)

This repository contains the companion code for the article *oTree: Writing short and efficient code for experiments with dynamically determined data quantity* to be published in a Special Issue on "Software for Experimental Economics" in the *Journal of Behavioral and Experimental Finance*.

The experiment "market" that is provided as [oTree](http://www.otree.org/) application serves as a illustrative example for a simple stylized market simulation. Many individuals (1 ... *N*-1) are selling fruit. In each round, these sellers choose a kind of fruit and a selling price, whereas individual *N* (the buyer) needs to choose from which of those offers to buy. The implemenation follows the principle suggested in the paper, relying on "custom data models" from oTree's underlying Django framework. The well documented source code resides in the `market` directory.  

**Please note:** This is not a complete experiment but only a stripped-down example for illustrative purposes. This means for example, that some sanity checks like checking for negative balances are not implemented.

## License

Apache License 2.0. See LICENSE file.
