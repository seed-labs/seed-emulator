'''
Codes adapted from NS3 Propagation Loss Model:
https://www.nsnam.org/docs/models/html/propagation.html#threegpppropagationlossmodel
'''
"""
Copyright (c) 2020 SIGNET Lab, Department of Information Engineering,
University of Padova

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation;

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from ..NodeInfo import NodeInfo
from .PropagationLossModel import *
from ..conditionModel import *
import numpy as np
from collections import namedtuple
from scipy.stats import norm
from scipy.stats import lognorm

M_PI    = 3.14159265358979323846
# propagation velocity in free space
M_C     = 3.0e8
ShadowingMapItem = namedtuple('ShadowingMapItem', ['shadowing', 'condition', 'distance'])

class ThreeGppPropagationLossModel(PropagationLossModel):
    frequency:float
    channelConditionModel:ThreeGppConditionModel
    '''
    Shadowing effects are defined as 
    the effects of received signal power fluctuations 
    due to obstruction between the transmitter and receiver. 
    Therefore, the signal changes as a result of the shadowing 
    mainly come from reflection and scattering during transmittal.
    '''
    shadowingEnabled:bool
    shadowingMap:dict
    enforceRangesEnabled:bool

    def __init__(self, frequency, channelConditionModel:ChannelConditionModel):
        super().__init__()
        self.frequency = frequency
        self.channelConditionModel = channelConditionModel
        self.shadowingEnabled = False
        self.shadowingMap = {}
        self.enforceRangesEnabled = False

    def getChannelType(self):
        return "ThreeGpp"
    
    def getChannelConditionModel(self):
        return self.channelConditionModel
    
    def convertMuSigmaFromLogNormalToNormal(mu, sigma):
        norm_mu = 2*np.log(mu) - np.log(sigma*sigma + mu*mu)/2
        norm_sigma = -2*np.log(mu) + np.log(sigma*sigma + mu*mu)

        return norm_mu, norm_sigma
    '''
    in the seed simulator, we do not calculate the rxPower directly.
    '''
    def doCalcRxPower(self, txPower, node_a: NodeInfo, node_b: NodeInfo):
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()

        distance2D = self.getDistance2D(a_position, b_position)
        distance3D = self.getDistance3D(a_position, b_position)
        
        cond = self.channelConditionModel.getChannelCondition(node_a, node_b)
        # get heights of user terminal and base station
        # higher one is base station
        ut_height, bs_height = self.getUtAndBsHeight(a_position, b_position)

        rxPower = txPower
        loss = self.getLoss(cond, distance2D, distance3D, ut_height, bs_height)
        rxPower = rxPower - loss

        '''
        P(rxPower* - losLoss* - nlosvAdditionalLoss - shadowing < threshold) (*: constant)
        '''
        if self.shadowingEnabled:
            shadowing = self.getShadowing(node_a, node_b, cond.getLosCondition())
            rxPower = rxPower - shadowing
            print("shadowing enabled and its value is ", shadowing)   

        return rxPower
    
    def calcLossRate(self, node_a: NodeInfo, node_b: NodeInfo, txPower=None, threshold=None):
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()

        distance2D = self.getDistance2D(a_position, b_position)
        distance3D = self.getDistance3D(a_position, b_position)
        # print(node_a.id, node_b.id)
        cond = self.channelConditionModel.getChannelCondition(node_a, node_b)
        # get heights of user terminal and base station
        # higher one is base station
        ut_height, bs_height = self.getUtAndBsHeight(a_position, b_position)

        if threshold==None:
            threshold = self.threshold

        isShadowingEnabled = False
        isNlosV = False
        isNlosVNoAdditionalLoss = False

        if self.shadowingEnabled:
            mu_ln_shadowing, sigma_ln_shadowing = self.getMuSigmaForShadowing(node_a, node_b, cond.getLosCondition())
            isShadowingEnabled = True
        if cond.getLosCondition() == LosConditionValue.NLOSv:
            if self.getMuSigmaForNlovLossDistribution(distance3D, ut_height, bs_height):
                mu_ln_nlosv, sigma_ln_nlosv = self.getMuSigmaForNlovLossDistribution(distance3D, ut_height, bs_height)
                isNlosV = True
            else:
                isNlosVNoAdditionalLoss = True

        if isShadowingEnabled and isNlosV:
            # P(rxPower - losslos - (X+Y) < threshold) : X shadowing variable, Y nlosv variable
            # P( X+Y > rxPower - losslos - threshold ):
            # 1 - P (X+Y<rxPower-losslos-threshold):
            mu_shadowing, sigma_shadowing = self.convertMuSigmaFromLogNormalToNormal(mu_ln_shadowing, sigma_ln_shadowing)
            mu_nlosv, sigma_nlosv = self.convertMuSigmaFromLogNormalToNormal(mu_ln_nlosv, sigma_ln_nlosv)

            mu_sum = mu_shadowing + mu_nlosv
            sigma_sum = np.sqrt(sigma_shadowing**2 + sigma_nlosv**2)

            lossLos = self.getLossLos(distance2D, distance3D, ut_height, bs_height) 
            newThreshold = txPower - lossLos - threshold
            lossRate = 1- norm.cdf(newThreshold, sigma=sigma_sum, mu=mu_sum) * 100

            return round(lossRate,2)
        elif isShadowingEnabled:
            loss = self.getLoss(cond, distance2D, distance3D, ut_height, bs_height)
            rxPower = txPower - loss
            '''
            P(rxPower - shadowingValue < threshold) : Probability to have (rxPower - shadowingValue) below threshold. = loss rate 
            = 1 - P(shadowingValue < rxPower - threshold)
            
            '''
            newThreshold = rxPower - threshold
            loss_rate = (1 - lognorm.cdf(x=newThreshold, s=sigma_ln_shadowing, scale=np.exp(mu_ln_shadowing))) * 100
            return round(loss_rate, 2)
        elif isNlosV:
            # P(rxPower - losslos - lossnlosv < threshold)
        #   # = P(lossnlosv > rxPower-threshold - losslos)
        #   # = 1 - P( lossnlosv < rxPower-threshold - losslos)
            lossLos = self.getLossLos(distance2D, distance3D, ut_height, bs_height)
            newThreshold = txPower - threshold - lossLos
            lossRate = (1 - lognorm.cdf(x=newThreshold, scale=np.exp(mu_ln_nlosv), s=sigma_ln_nlosv)) * 100
            return round(lossRate,2)
        elif isNlosVNoAdditionalLoss:
            loss = self.getLossLos(distance2D, distance3D, ut_height, bs_height)
            rxPower = txPower - loss
            if rxPower > threshold:
                return 0.0
            else:
                return 1.0 * 100

        else:
            loss = self.getLoss(cond, distance2D, distance3D, ut_height, bs_height)
            rxPower = txPower - loss
            if rxPower > threshold:
                return 0.0
            else:
                return 1.0 * 100

        # if not self.shadowingEnabled:
        #     if cond.getLosCondition() == LosConditionValue.NLOSv:
        #         # P(rxPower - losslos - lossnlosv < threshold)
        #         # = P(loss > rxPower-threshold - losslos)
        #         # = 1 - P( loss < rxPower-threshold - losslos)
        #         lossLos = self.getLossLos(distance2D, distance3D, ut_height, bs_height) 

        #         # thres = rxPower - threshold - losslos
        #         thres = txPower - threshold - lossLos
        #         if self.getMuSigmaForNlovLossDistribution(distance3D, ut_height, bs_height) == None:
        #             if rxPower > threshold:
        #                 return 0.0
        #             else:
        #                 return 1.0 * 100
        #         else: 
        #             mu, sigma = self.getMuSigmaForNlovLossDistribution(distance3D, ut_height, bs_height)
        #             loss_rate = (1 - lognorm.cdf(x=thres, scale=np.exp(mu), s=sigma)) * 100
        #             return round(loss_rate, 2)
        #     else:
        #         if rxPower > threshold:
        #             return 0.0
        #         else:
        #             return 1.0 * 100
        # else:
        #     if cond.getLosCondition() == LosConditionValue.NLOSv:
        #         # P(rxPower - losslos - lossnlosv < threshold)
        #         # = P(loss > rxPower-threshold - losslos)
        #         # = 1 - P( loss < rxPower-threshold - losslos)
        #         lossLos = self.getLossLos(distance2D, distance3D, ut_height, bs_height)
        #         # thres = rxPower - threshold - losslos
        #         thres = txPower - threshold - lossLos
                
        #         loss_rate = (1 - self.getAdditionalNlosvLossProbability(distance3D, ut_height, bs_height, thres))*100
        #         return round(loss_rate, 2)
        #     else:
        #         '''
        #         P(rxPower - shadowingValue < threshold)
        #         '''
                
        #         '''
        #         Case 1)
        #         P(rxPower - shadowingValue < threshold) : Probability to have (rxPower - shadowingValue) below threshold. = loss rate 
        #         = P(rxPower - random_value * shadowingStd < threshold)
        #         = P(random_value > (rxPower - threshold)/shadowingStd)
        #         = 1 - P(random_value < (rxPower - threshold/shadowingStd)) => thres = (rxPower - threshold/shadowingStd)
        #         '''
        #         # thres = self.getShadowingThreshold(node_a, node_b, cond.getLosCondition(), rxPower, threshold)
        #         '''
        #         P(rxPower - shadowingValue < threshold) : Probability to have (rxPower - shadowingValue) below threshold. = loss rate 
        #         = P(random_value > (rxPower - threshold)/shadowingStd)
        #         = 1 - P(shadowingValue < rxPower - threshold)
                
        #         '''
        #         mu,sigma = self.getMuSigmaForShadowing(node_a, node_b, cond.getLosCondition())
        #         loss_rate = (1 - lognorm.cdf(x=threshold, s=sigma, scale=np.exp(mu)))
        #         # P(x<thres)
        #         # loss_rate = (1 - norm.cdf(x=thres, loc=0, scale=1)) * 100
        #         return round(loss_rate, 2)


    

    def getLoss(self, channelCondition:ChannelCondition, distance2D, distance3D, utHeight, bsHeight):
        loss = 0

        # line of sight condition
        losCondition = channelCondition.getLosCondition()
        if losCondition == LosConditionValue.LOS:
            loss = self.getLossLos(distance2D, distance3D, utHeight, bsHeight)
        elif losCondition == LosConditionValue.NLOS:
            loss = self.getLossNlos(distance2D, distance3D, utHeight, bsHeight)
        elif losCondition == LosConditionValue.NLOSv:
            loss = self.getLossNlosv(distance2D, distance3D, utHeight, bsHeight)
        return loss
    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        pass

    def getLossNlos(self, distance2D, distance3D, utHeight, bsHeight):
        pass

    def getLossNlosv(self, distance2D, distance3D, utHeight, bsHeight):
        pass

    def getUtAndBsHeight(self, a_position, b_position):
        hUt = min(a_position.z, b_position.z)
        hBs = max(a_position.z, b_position.z)
        return (hUt, hBs)

    def getKey(self, node_a:NodeInfo, node_b:NodeInfo):
        x1 = min(node_a.id, node_b.id)
        x2 = max(node_a.id, node_b.id)

        key = (((x1 + x2) * (x1 + x2 + 1)) / 2) + x2
        
        return key
    
    def getShadowing(self, node_a:NodeInfo, node_b:NodeInfo, cond:LosConditionValue):
        shadowingValue = 0.0
        
        notFound = False
        newCondition = False
        newDistance:Vector
        # https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/16.01.00_60/tr_138901v160100p.pdf
        key = self.getKey(node_a, node_b)
        if key in self.shadowingMap.keys():
            item:ShadowingMapItem = self.shadowingMap[key]
            newCondition = (item.condition != cond)
            newDistance = self._getVectorDifference(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        else:
            notFound = True
            self.shadowingMap[key] = ShadowingMapItem(0.0, cond, Vector(0,0,0))
        
        item:ShadowingMapItem = self.shadowingMap[key]

        if (notFound or newCondition):
            random_value = np.random.normal(0,1)
            shadowingValue = random_value * self.getShadowingStd(node_a, node_b, cond)
        # Auto correlation model
        else:
            R = np.exp(-1 * self._getDisplacementLen2D(newDistance, item.distance) / self.getShadowingCorrelationDistance(cond))
            shadowingValue = R * item.shadowing + np.sqrt( 1- R*R ) * np.random.normal(0, 1) * self.getShadowingStd(node_a, node_b, cond)

        item._replace(shadowing = shadowingValue)
        item._replace(condition = cond)
    
        return shadowingValue
    
    def getMuSigmaForShadowing(self, node_a:NodeInfo, node_b:NodeInfo, cond:LosConditionValue):
        shadowingValue = 0.0
        
        notFound = False
        newCondition = False
        newDistance:Vector
        # https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/16.01.00_60/tr_138901v160100p.pdf
        key = self.getKey(node_a, node_b)
        if key in self.shadowingMap.keys():
            item:ShadowingMapItem = self.shadowingMap[key]
            newCondition = (item.condition != cond)
            newDistance = self._getVectorDifference(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        else:
            notFound = True
            self.shadowingMap[key] = ShadowingMapItem(0.0, cond, Vector(0,0,0))
        
        item:ShadowingMapItem = self.shadowingMap[key]

        if (notFound or newCondition):
            mu = 0
            sigma = self.getShadowingStd(node_a, node_b, cond)
            # need to change lognormal not normal
            # random_value = np.random.normal(0,1)
            # shadowingValue = random_value * self.getShadowingStd(node_a, node_b, cond)
            shadowingValue = np.random.lognormal(mean=mu, sigma=sigma)
        # Auto correlation model
        else:
            R = np.exp(-1 * self._getDisplacementLen2D(newDistance, item.distance) / self.getShadowingCorrelationDistance(cond))
            mu = R * item.shadowing
            sigma = np.sqrt( 1- R*R ) * self.getShadowingStd(node_a, node_b, cond)
            # shadowingValue = R * item.shadowing + np.sqrt( 1- R*R ) * np.random.normal(0, 1) * self.getShadowingStd(node_a, node_b, cond)
            shadowingValue = np.random.lognormal(mean=mu, sigma=sigma)
        item._replace(shadowing = shadowingValue)
        item._replace(condition = cond)
    
        return mu, sigma
    
    def getShadowingThreshold(self, node_a:NodeInfo, node_b:NodeInfo, cond:LosConditionValue, rxpower, threshold):
        shadowingValue = 0.0
        
        notFound = False
        newCondition = False
        newDistance:Tuple

        key = self.getKey(node_a, node_b)
        if key in self.shadowingMap.keys():
            item:ShadowingMapItem = self.shadowingMap[key]
            newCondition = (item.condition != cond)
            newDistance = self._getVectorDifference(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        else:
            notFound = True
            self.shadowingMap[key] = ShadowingMapItem(0.0, cond, Vector(0,0,0))
        
        item:ShadowingMapItem = self.shadowingMap[key]

        if (notFound or newCondition):
            '''
            P(rxPower - shadowingValue < threshold) : Probability to have (rxPower - shadowingValue) below threshold. = loss rate 
            = P(rxPower - random_value * shadowingStd < threshold)
            = P(random_value > (rxPower - threshold)/shadowingStd)
            = 1 - P(random_value < (rxPower - threshold/shadowingStd))
            '''
            result = (rxpower - threshold) / self.getShadowingStd(node_a, node_b, cond)
            random_value = np.random.normal(0,1)
            shadowingValue = random_value * self.getShadowingStd(node_a, node_b, cond)
        else:
            '''
            P(rxPower - shadowingValue < threshold) : Probability to have (rxPower - shadowingValue) below threshold. = loss rate 
            = P(rxPower - R * item.shadowing - np.sqrt( 1- R*R ) * random_value * shadowingStd < threshold)
            = P(np.sqrt( 1- R*R ) * random_value * shadowingStd > rxPower - R * item.shadowing -threshold)
            = P(random_value > (rxPower - R * item.shadowing -threshold) / (np.sqrt( 1- R*R ) * shadowingStd))
            = 1 - P(random_value < (rxPower - R * item.shadowing -threshold) / (np.sqrt( 1- R*R ) * shadowingStd))
            '''
            R = np.exp(-1 * self._getDisplacementLen2D(newDistance, item.distance) / self.getShadowingCorrelationDistance(cond))
            result = (rxpower - R*item.shadowing - threshold) / (np.sqrt(1-R*R)*self.getShadowingStd(node_a, node_b, cond))
            shadowingValue = R * item.shadowing + np.sqrt( 1- R*R ) * np.random.normal(0, 1) * self.getShadowingStd(node_a, node_b, cond)

        item._replace(shadowing = shadowingValue)
        item._replace(condition = cond)

        return result
    
    def getShadowingStd(self, node_a:NodeInfo, node_b:NodeInfo, cond:LosConditionValue):
        '''
        Returns the shadow fading standard deviation
        '''
        pass

    def getShadowingCorrelationDistance(self, cond:LosConditionValue):
        '''
        Returns the shadow fading correlation distance
        '''
        pass

class ThreeGppRmaPropagationLossModel(ThreeGppPropagationLossModel):
    avgBuildingHeight:float
    avgStreetWidth:float

    def __init__(self, frequency, channelConditionModel):
        super().__init__(frequency, channelConditionModel)
        self.avgBuildingHeight = 5.0
        self.avgStreetWidth = 20.0
    
    def getBpDistance(self, frequency, hA, hB):
        # M_C = 3.0e8 : propagation velocity in free space
        distanceBp = 2.0 * M_PI * hA * hB * frequency / M_C
        return distanceBp
    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (self.frequency <= 30.0e9), "RMa scenario is valid for frequencies between 0.5 and 30 GHz."
        
        assert not self.enforceRangesEnabled or (utHeight >= 1.0 and utHeight <= 10.0), "The height of the UT should be between 1 and 10 m"
        assert not self.enforceRangesEnabled or (bsHeight >= 10.0 and bsHeight <= 150.0), "The height of the BS should be between 10 and 150 m"
        np.seterr(divide = 'ignore')
        distanceBp = self.getBpDistance(self.frequency, bsHeight, utHeight)
        loss =  20.0 * np.log10(40.0 * M_PI * distance3D * self.frequency / 1e9 / 3.0) +\
                  min(0.03 * pow(self.avgBuildingHeight, 1.72), 10.0) * np.log10(distance3D) -\
                  min(0.044 * pow(self.avgBuildingHeight, 1.72), 14.77) + 0.002 * np.log10(self.avgBuildingHeight) * distance3D
        
        if distance2D > distanceBp:
            loss = loss + 40 * np.log10(distance3D/distanceBp)
            
        return loss
    
    def getLossNlos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (self.frequency <= 30.0e9), "RMa scenario is valid for frequencies between 0.5 and 30 GHz."

        assert not self.enforceRangesEnabled or (utHeight >= 1.0 and utHeight <= 10.0), "The height of the UT should be between 1 and 10 m"
        assert not self.enforceRangesEnabled or (bsHeight >= 10.0 and bsHeight <= 150.0), "The height of the BS should be between 10 and 150 m"

        plNlos = 161.04 - 7.1 * np.log10(self.avgStreetWidth) + 7.5 * np.log10(self.avgBuildingHeight) - \
                    (24.37 - 3.7 * pow((self.avgBuildingHeight / bsHeight), 2)) * np.log10(bsHeight) + \
                    (43.42 - 3.1 * np.log10(bsHeight)) * (np.log10(distance3D) - 3.0) + \
                    20.0 * np.log10(self.frequency / 1e9) - (3.2 * pow(np.log10(11.75 * utHeight), 2) - 4.97)
        
        loss = max(self.getLossLos(distance2D, distance3D, utHeight, bsHeight), plNlos)
        return loss
    
    def getShadowingStd(self, node_a: NodeInfo, node_b: NodeInfo, cond: LosConditionValue):
        shadowingStd = 0.0
        if cond == LosConditionValue.LOS:
            shadowingStd = 0.0
            hA = node_a.getMobility().getPosition().z
            hB = node_b.getMobility().getPosition().z
            distance2D = self.getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
            distanceBp = self.getBpDistance(self.frequency, hA, hB)

            if (distance2D <= distanceBp):
                shadowingStd = 4.0
            else:
                shadowingStd = 6.0
        elif cond == LosConditionValue.NLOS:
            shadowingStd = 8.0

        return shadowingStd
    
    def getShadowingCorrelationDistance(self, cond: LosConditionValue):
        correlationDistance = 0.0
        if cond == LosConditionValue.LOS:
            correlationDistance = 37
        elif cond == LosConditionValue.NLOS:
            correlationDistance = 120

        return correlationDistance
    
class ThreeGppUmaPropagationLossModel(ThreeGppPropagationLossModel):
    def __init__(self, frequency, channelConditionModel):
        super().__init__(frequency, channelConditionModel)
    
    def getBpDistance(self, hUt, hBs, distance2D):
        # M_C = 3.0e8 : propagation velocity in free space
        
        # compute g (d2D) (see 3GPP TR 38.901, Table 7.4.1-1, Note 1)
        g = 0.0
        if (distance2D > 18.0):
            g = 5.0 / 4.0 * pow(distance2D / 100.0, 3) * np.exp(-distance2D / 150.0)
        
        # compute C (hUt, d2D) (see 3GPP TR 38.901, Table 7.4.1-1, Note 1)
        c = 0.0
        if (hUt >= 13.0):
            c = pow((hUt - 13.0) / 10.0, 1.5) * g
        

        #compute hE (see 3GPP TR 38.901, Table 7.4.1-1, Note 1)
        # hE = effective height
        # "effective height" typically refers to the height above ground 
        # level at which an antenna or radiating element appears to operate 
        # for the purpose of calculating signal propagation and coverage
        prob = 1.0 / (1.0 + c)
        hE = 0.0
        if np.random.uniform(0,1) < prob:
            hE = 1.0
        else:
            random = np.random.randint(12, max(12, int(hUt - 1.5)))
            hE = np.floor(random / 3.0) * 3.0

        # compute dBP' (see 3GPP TR 38.901, Table 7.4.1-1, Note 1)
        distanceBp = 4 * (hBs - hE) * (hUt - hE) * self.frequency / M_C

        return distanceBp
    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (utHeight >= 1.4 and utHeight <= 22.5), "The height of the UT should be between 1 and 10 m"
        assert not self.enforceRangesEnabled or bsHeight == 25.0, "The height of the BS should be between 10 and 150 m"

        distanceBp = self.getBpDistance(utHeight, bsHeight, distance2D)

        assert not self.enforceRangesEnabled or (distance2D >= 10.0 and distance2D <= 5.0e3), "Uma 2D distance out of range"

        loss =  28.0 + 22.0 * np.log10(distance3D) + 20.0 * np.log10(self.frequency/1e9)

        if distance2D > distanceBp:
            loss = loss - 9.0 * np.log10(pow(distanceBp, 2) + pow(bsHeight - utHeight, 2))

        return loss
    
    def getLossNlos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (utHeight >= 1.5 and utHeight < 10.0 ), "The height of the UT should be between 1.5 and 10 m"
        assert not self.enforceRangesEnabled or (bsHeight == 10.0), "The height of the BS should be between 10  m"

        assert not self.enforceRangesEnabled or (distance2D >= 10.0 and distance2D <= 5.0e3), "Uma 2D distance out of range"
        
        plNlos = 22.4 + 35.3 * np.log10(distance3D) + 21.3 * np.log10(self.frequency / 1e9) - 0.3 * (utHeight - 1.5)

        loss = max(self.getLossLos(distance2D, distance3D, utHeight, bsHeight), plNlos)

        return loss
    
    def getShadowingStd(self, node_a: NodeInfo, node_b: NodeInfo, cond: LosConditionValue):
        shadowingStd = 0
        if cond == LosConditionValue.LOS:
            shadowingStd = 4.0
        elif cond == LosConditionValue.NLOS:
            shadowingStd = 7.82
        return shadowingStd
    
    def getShadowingCorrelationDistance(self, cond: LosConditionValue):
        correlationDistance = 0.0
        if cond == LosConditionValue.LOS:
            correlationDistance = 10
        elif cond == LosConditionValue.NLOS:
            correlationDistance = 13

        return correlationDistance
    
class ThreeGppUmiStreetCanyonPropagationLossModel(ThreeGppPropagationLossModel):
    def __init__(self, frequency, channelConditionModel):
        super().__init__(frequency, channelConditionModel)
    
    def getBpDistance(self, hUt, hBs, distance2D):
        # M_C = 3.0e8 : propagation velocity in free space
        
        hE = 1.0

        distanceBp = 4 * (hBs - hE) * (hUt - hE) * self.frequency / M_C

        return distanceBp
    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (utHeight >= 1.5 and utHeight <= 10.0), "The height of the UT should be between 1.5 and 10 m"
        assert not self.enforceRangesEnabled or bsHeight == 10.0, "The height of the BS should be 10 m"

        distanceBp = self.getBpDistance(utHeight, bsHeight, distance2D)

        assert not self.enforceRangesEnabled or (distance2D >= 10.0 and distance2D <= 5.0e3), "UmiStreetCanyon 2D distance out of range"

        loss =  32.4 + 21.0 * np.log10(distance3D) + 20.0 * np.log10(self.frequency / 1e9)

        if distance2D > distanceBp:
            loss = loss - 9.5 * np.log10(pow(distanceBp, 2) + pow(bsHeight - utHeight, 2))

        return loss
    
    def getLossNlos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (utHeight >= 1.4 and utHeight <= 22.5), "The height of the UT should be between 1 and 10 m"
        assert not self.enforceRangesEnabled or (bsHeight == 25.0), "The height of the BS should be between 10 and 150 m"

        assert not self.enforceRangesEnabled or (distance2D >= 10.0 and distance2D <= 5.0e3), "Uma 2D distance out of range"
        
        plNlos = 13.54 + 39.08 * np.log10(distance3D) + 20.0 * np.log10(self.frequency / 1e9) - 0.6 * (utHeight - 1.5)

        loss = max(self.getLossLos(distance2D, distance3D, utHeight, bsHeight), plNlos)

        return loss
    
    def getShadowingStd(self, node_a: NodeInfo, node_b: NodeInfo, cond: LosConditionValue):
        if cond == LosConditionValue.LOS:
            shadowingStd = 4.0
        elif cond == LosConditionValue.NLOS:
            shadowingStd = 6.0

        return shadowingStd
    
    def getShadowingCorrelationDistance(self, cond: LosConditionValue):
        correlationDistance = 0.0
        if cond == LosConditionValue.LOS:
            correlationDistance = 37
        elif cond == LosConditionValue.NLOS:
            correlationDistance = 50

        return correlationDistance

class ThreeGppIndoorOfficePropagationLossModel(ThreeGppPropagationLossModel):
    def __init__(self, frequency, channelConditionModel):
        super().__init__(frequency, channelConditionModel)

    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (distance3D >= 1.0 and distance3D <= 150), "IndoorOffice 3D distance out of range"

        loss = 32.4 + 17.3 * np.log10(distance3D) + 20.0 * np.log10(self.frequency / 1e9)
        
        return loss
    
    def getLossNlos(self, distance2D, distance3D, utHeight, bsHeight):
        assert not self.enforceRangesEnabled or (distance3D >= 1.0 and distance3D <= 150), "IndoorOffice 3D distance out of range"

        plNlos = 17.3 + 38.3 * np.log10(distance3D) + 24.9 * np.log10(self.frequency / 1e9)

        loss = max(self.getLossLos(distance2D, distance3D, utHeight, bsHeight), plNlos)

        return loss
    
    def getShadowingStd(self, node_a: NodeInfo, node_b: NodeInfo, cond: LosConditionValue):
        shadowingStd = 0.0
        if cond == LosConditionValue.LOS:
            shadowingStd = 3.0
        elif cond == LosConditionValue.NLOS:
            shadowingStd = 8.03

        return shadowingStd
    
    def getShadowingCorrelationDistance(self, cond: LosConditionValue):
        correlationDistance = 0.0
        if cond == LosConditionValue.LOS:
            correlationDistance = 10
        elif cond == LosConditionValue.NLOS:
            correlationDistance = 6

        return correlationDistance


class ThreeGppV2vUrbanPropagationLossModel(ThreeGppPropagationLossModel):

    # The persentage of vehicles of type 3 (i.e., trucks) in the scenario
    percType3Vehicles:float
    def __init__(self, frequency, channelConditionModel):
        super().__init__(frequency, channelConditionModel)
        self.percType3Vehicles = 0.0

    def getChannelType(self):
        return "ThreeGppV2v"
    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        np.seterr(divide = 'ignore')
        loss = 38.77 + 16.7 * np.log10(distance3D) + 18.2 * np.log10(self.frequency / 1e9)
        
        return loss
    
    def getLossNlosv(self, distance2D, distance3D, utHeight, bsHeight):
        loss = self.getLossLos(distance2D, distance3D, utHeight, bsHeight) \
            + self.getAdditionalNlosvLoss(distance3D, utHeight, bsHeight)

        return loss
    
    def getAdditionalNlosvLoss(self, distance3D, utHeight, bsHeight):
        additionalLoss = 0
        blockerHeight = 0
        mu_a = 0
        sigma_a = 0
        randomValue = np.random.uniform(0, 100)

        if (randomValue < self.percType3Vehicles):
            # vehicles of type 3 have height 3 meters
            blockerHeight = 3.0
        else:
            # vehicles of type 1 and 2 have height 1.6 meters
            blockerHeight = 1.6

        if min(utHeight, bsHeight) > blockerHeight:
            additionalLoss = 0
        elif max(utHeight, bsHeight) < blockerHeight:
            mu_a = 9.0 + max(0.0, 15 * np.log10(distance3D) - 41.0)
            sigma_a = 4.5
            
            mu = np.log(pow(mu_a, 2) / np.sqrt(pow(sigma_a, 2) + pow(mu_a, 2)))
            sigma = np.sqrt(np.log(pow(sigma_a, 2)/ pow(mu_a, 2) + 1))
            additionalLoss = max(0.0, np.random.lognormal(mu, sigma))
            # print("mu ", mu, "sigma ", sigma, "additionalLoss ", additionalLoss)

        else:
            mu_a = 5.0 + max(0.0, 15*np.log10(distance3D)-41.0)
            sigma_a = 4.0

            mu = np.log(pow(mu_a, 2) / np.sqrt(pow(sigma_a, 2) + pow(mu_a, 2)))
            sigma = np.sqrt(np.log(pow(sigma_a, 2)/ pow(mu_a, 2) + 1 ))
            
            additionalLoss = max(0.0, np.random.lognormal(mu, sigma))

        # print("NlosV Additional: ", additionalLoss)
        return additionalLoss
    
    # return P(lossnlosv < threshold)
    '''
    f() : pdf of additional loss (inside this we have random value)
    P(*rxPower - *loss - additionalLoss < threshold) = loss rate (*: fixed)
    P(additionalLoss >  rxPower - threshold - loss)
    '''
    def getAdditionalNlosvLossProbability(self, distance3D, utHeight, bsHeight, threshold):
        blockerHeight = 0
        mu_a = 0
        sigma_a = 0
        randomValue = np.random.uniform(0, 100)

        if (randomValue < self.percType3Vehicles):
            # vehicles of type 3 have height 3 meters
            blockerHeight = 3.0
        else:
            # vehicles of type 1 and 2 have height 1.6 meters
            blockerHeight = 1.6

        if min(utHeight, bsHeight) > blockerHeight:
            if 0 < threshold:
                return 1.0
            else:
                return 0.0
            
        elif max(utHeight, bsHeight) < blockerHeight:
            mu_a = 9.0 + max(0.0, 15 * np.log10(distance3D) - 41.0)
            sigma_a = 4.5
            
            mu = np.log(pow(mu_a, 2) / np.sqrt(pow(sigma_a, 2) + pow(mu_a, 2)))
            sigma = np.sqrt(np.log(pow(sigma_a, 2)/ pow(mu_a, 2) + 1))
            # additionalLoss = max(0.0, np.random.lognormal(mu, sigma))
            probability = lognorm.cdf(x=threshold, scale=np.exp(mu), s=sigma)
            return probability
            # print("mu ", mu, "sigma ", sigma, "additionalLoss ", additionalLoss)

        else:
            mu_a = 5.0 + max(0.0, 15*np.log10(distance3D)-41.0)
            sigma_a = 4.0

            mu = np.log(pow(mu_a, 2) / np.sqrt(pow(sigma_a, 2) + pow(mu_a, 2)))
            sigma = np.sqrt(np.log(pow(sigma_a, 2)/ pow(mu_a, 2) + 1 ))
            
            # additionalLoss = max(0.0, np.random.lognormal(mu, sigma))
            probability = lognorm.cdf(x=threshold, scale=np.exp(mu), s=sigma)
            return probability
    
    def getMuSigmaForNlovLossDistribution(self, distance3D, utHeight, bsHeight):
        blockerHeight = 1.6

        if min(utHeight, bsHeight) > blockerHeight:
            # no additional loss
            return None
        elif max(utHeight, bsHeight) < blockerHeight:
            mu_a = 9.0 + max(0.0, 15 * np.log10(distance3D) - 41.0)
            sigma_a = 4.5
        else:
            mu_a = 5.0 + max(0.0, 15*np.log10(distance3D)-41.0)
            sigma_a = 4.0

        mu = np.log(pow(mu_a, 2) / np.sqrt(pow(sigma_a, 2) + pow(mu_a, 2)))
        sigma = np.sqrt(np.log(pow(sigma_a, 2)/ pow(mu_a, 2) + 1 ))

        return mu, sigma
    
            
    def getLossNlos(self, distance2D, distance3D, utHeight, bsHeight):
        loss = 36.85 + 30 * np.log10(distance3D) + 18.9 * np.log10(self.frequency / 1e9)

        return loss
    
    def getShadowingStd(self, node_a: NodeInfo, node_b: NodeInfo, cond: LosConditionValue):
        if cond == LosConditionValue.LOS or cond == LosConditionValue.NLOSv:
            shadowingStd = 3.0
        elif cond == LosConditionValue.NLOS:
            shadowingStd = 4.0

        return shadowingStd
    
    def getShadowingCorrelationDistance(self, cond: LosConditionValue):
        correlationDistance = 0.0
        if cond == LosConditionValue.LOS:
            correlationDistance = 10
        elif cond == LosConditionValue.NLOS or cond == LosConditionValue.NLOSv:
            correlationDistance = 13

        return correlationDistance

class ThreeGppV2vHighwayPropagationLossModel(ThreeGppV2vUrbanPropagationLossModel):

    # The persentage of vehicles of type 3 (i.e., trucks) in the scenario
    percType3Vehicles:float
    def __init__(self, frequency, channelConditionModel):
        super().__init__(frequency, channelConditionModel)
        self.percType3Vehicles = 0.0

    
    def getLossLos(self, distance2D, distance3D, utHeight, bsHeight):
        
        loss = 32.4 + 20 * np.log10(distance3D) + 20 * np.log10(self.frequency / 1e9)
        
        return loss