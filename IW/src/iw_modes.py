#IW_MODES
#Desc : Library for solving vertical modes of internal waves
#Auth : J. DeFilippis
#Date : 2-15-2019

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_bvp, quad,trapz
from scipy.linalg import eig ,inv

class InternalWaveModes:
    """
    Desc: 
    A class to generate internal wave vertical modes via different
    numerical methods

    Attributes:
       depth : array
         A depth coordinate of choice meters,pressure etc
       strat : func
         A function of stratification whose arguement is the 
         depth coordinate strat(depth)
    """

    def __init__(self,depth,N2=np.array([]),freq=0,f=1.1583e-5,
                 num_modes=1):
        """
        Parameters:
          depth : array
              vertical coordinate of modes
          N : func, or array
              stratification of medium
        """
        #Set Attributes
        self.set_attributes(depth,N2,freq,f,num_modes)

        #Generate Vertial Modes & Wavenumbers 
        lamb,vr = self.dmodes_evp()
        r      = self.normalize(vr)
        self.hwavenumbers =  np.sqrt( (self.freq**2 - f**2 ) / lamb )
        
        self.d_modes     = [ vr[:,m] for m in np.arange(0,len(vr)) ]
        self.p_modes     = self.pressure_modes()
        self.u_modes     = self.velocity_modes()


    def set_attributes(self,depth,N2,freq,f,num_modes):
        """
        Desc : Set various attributes for the class
        """
        self.depth = depth
        self.N2 = N2  if N2.size else self.cannonical_bfrq()
        self.freq = freq if freq > 0 else 2*np.pi/(3600*24)
        self.f = f   
        self.num_modes = num_modes 

 
    def dmodes_evp(self):
        """
        Desc : Solves helmoltz equation using an EVP solver 
               techique for interal wave vertical velocity 
        Returns:
               solution : array
                 A solution as a function of the depth coordinate
        """
        #Physical Properties
        H  = len(self.depth)
        delta = (self.depth[H-1] - self.depth[0])/H
        fsq = (self.freq)**2
        
        #FDM stencil for centered second derivative
        D2  = self.tri_fdm(H,delta)
        F2  = np.diag(np.ones(len(self.N2))*fsq)
        N2  = np.diag(self.N2)
        
        #Eigen value problem IW equation
        lamb,vr = eig((F2-N2),D2)
        
        return lamb,vr
    
        
    def pressure_modes(self):
        """
        Desc : 
        Generates pressure modes
        """
        p_modes = []
        for m in self.d_modes:
            omega = self.freq
            chi = -1025 * ((self.N2 - omega**2)) * m  
            p_mode  = [trapz(chi[0:i],self.depth[0:i]) for i in range(0,len(chi)) ]
            p_modes.append(np.array(p_mode))
        
        return p_modes
   
    
    def velocity_modes(self):
        """
        Desc : 
        Generates the horiztonal velocity modes
        """
        uv_modes = []
        sqdiff = (self.freq**2 - self.f**2)
        sqsum  = (self.freq**2 + self.f**2)
        for i,pm in enumerate(self.p_modes):
            kmag   = abs(self.hwavenumbers[i])
            uv = pm*kmag*np.sqrt(sqsum)/(1025*sqdiff)
            uv_modes.append(uv)
       
        return uv_modes


    def get_hwavenumber(self,mode_number):
        return self.hwavenumbers[mode_number]

    
    def normalize(self,vr):
        """
        Desc : 
        Normalizes each mode structure by finding the maximum
        amplitude mode and setting that to one
        """
        cur_max = 0
        for m in range(0,self.num_modes):
            new_max = max( abs(vr[:,m]) ) 
            cur_max = new_max if new_max > cur_max  else cur_max

        A = 1.0/cur_max if cur_max > 0 else 1
        
        for m in range(vr.shape[1]):
            vr[:,m] = A*vr[:,m]
        
        return vr

    
    #Consider making this more generic
    def tri_fdm(self, N, delta):
        """
        Desc : Generates a tri-diagonal matrix for 2nd order 
               derivative using a finite difference
        Returns :
                matrix : np matrix
        """
        ret = np.zeros(shape=(N,N))
        for i in range(1,N-1):
            ret[i,i]   = -2 
            ret[i,i-1] = 1 
            ret[i,i+1] = 1 
        
        ret[0,0]   = ret[N-1,N-1] = -2
        ret[0,1]   = ret[N-1,N-2] = 1

        ret /= delta**2

        return ret

    
    #Add the depth spacing to the stratifcation grad and check if this works for R script
    def cannonical_bfrq(self):
        """
        Desc:
        Cannonical example of a mid ocean Brunt Viasala frequency
        depth profile. Mainly for testing purposes
        """
        d = max(self.depth)
        diff  = np.average(np.diff(self.depth))
        sigma = 22 + np.tanh(2*np.pi*(self.depth- d*.15)/d)
        N2    = np.gradient(sigma,diff)/8
        return N2


    def mode_plot(self,n=3):
        """
        Desc : Generates a depth plot of stratriciation 
               against the first n modes
        Returns :
                fig,ax : matplotlib figure and axes
        """
        f, (ax1,ax2,ax3,ax4) = plt.subplots(1,4,sharey=True)
        
        #Stratification
        ax1.invert_yaxis()
        ax1.plot((3600/(2*np.pi))*np.sqrt(self.N2),self.depth)
        ax1.set_title("Stratification")
        ax1.set_xlabel("CPH")
    
        #Modes
        for i in np.arange(0,n):
            wm = self.d_modes[i]
            pm = self.p_modes[i]
            um = self.u_modes[i]
            ax2.plot(wm, self.depth, label="mode "+str(wm))
            ax3.plot(pm, self.depth, label="mode "+str(pm))
            ax4.plot(um, self.depth, label="mode "+str(um))
        ax2.set_title("D Modes")
        ax3.set_title("P Modes")
        ax4.set_title("U Modes")
       
        return f, (ax1,ax2) 
    
    
    #deprecated
    def dmodes_wkb(self,j):
        """
        Desc : Solves helmholtz equation using WKB
               approximation
        Params :
          j : int
              mode number
        Returns:
               solution : array
                 A solution as a function of the depth coordinate

        """
        
        #Integrate over stratification
        if callable(self.N2):
            No  = quad(self.N2,self.depth[-1],self.depth[0])[0]
            eta = np.vectorize(lambda z :  (1/No)*quad(self.N2,self.depth[-1],z)[0])
            self.modes = [ np.sin(np.pi*j*eta(self.depth)) for j in np.arange(0,len(self.depth)) ]
            return np.sin(np.pi*j*eta(self.depth))
        
        elif isinstance (self.N2, np.ndarray):
            No  = trapz(self.N2,self.depth)
            eta = np.vectorize( lambda zn : (1/No)*trapz(self.N2[zn:],self.depth[zn:]) )
            zn = np.arange(0,len(self.depth))
            self.modes = [ np.sin(np.pi*j*eta(zn)) for j in np.arange(0,len(self.depth)) ]
            return np.sin(np.pi*j*eta(zn))
        
        else:
            print("N needs to be an array or function")
            return
